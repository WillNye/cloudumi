import ujson as json

from cloudumi_common.config import config
from cloudumi_common.lib.account_indexers.aws_organizations import (
    retrieve_accounts_from_aws_organizations,
)
from cloudumi_common.lib.account_indexers.current_account import (
    retrieve_current_account,
)
from cloudumi_common.lib.account_indexers.local_config import (
    retrieve_accounts_from_config,
)
from cloudumi_common.lib.account_indexers.swag import retrieve_accounts_from_swag
from cloudumi_common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from cloudumi_common.lib.plugins import get_plugin_by_name
from cloudumi_common.models import CloudAccountModelArray

log = config.get_logger(__name__)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


async def cache_cloud_accounts(host) -> CloudAccountModelArray:
    """
    Gets Cloud Account Information from either ConsoleMe's configuration, AWS Organizations, or Swag,
    depending on configuration
    :return:
    """
    account_mapping = None
    # Get the accounts
    if config.get_host_specific_key(
        f"site_configs.{host}.cache_cloud_accounts.from_aws_organizations", host
    ):
        account_mapping = await retrieve_accounts_from_aws_organizations(host)
    elif config.get_host_specific_key(
        f"site_configs.{host}.cache_cloud_accounts.from_swag", host
    ):
        account_mapping = await retrieve_accounts_from_swag(host)
    elif config.get_host_specific_key(
        f"site_configs.{host}.cache_cloud_accounts.from_config", host, True
    ):
        account_mapping = await retrieve_accounts_from_config(host)

    if not account_mapping or not account_mapping.accounts:
        account_mapping = await retrieve_current_account(host)

    account_id_to_name = {}

    for account in account_mapping.accounts:
        account_id_to_name[account.id] = account.name

    redis_key = config.get_host_specific_key(
        f"site_configs.{host}.cache_cloud_accounts.redis.key.all_accounts_key",
        host,
        f"{host}_ALL_AWS_ACCOUNTS",
    )

    s3_bucket = None
    s3_key = None
    if config.region == config.get_host_specific_key(
        f"site_configs.{host}.celery.active_region", host, config.region
    ) or config.get_host_specific_key(f"site_configs.{host}.environment", host) in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_host_specific_key(
            f"site_configs.{host}.cache_cloud_accounts.s3.bucket", host
        )
        s3_key = config.get_host_specific_key(
            f"site_configs.{host}.cache_cloud_accounts.s3.file",
            host,
            "cache_cloud_accounts/accounts_v1.json.gz",
        )
    # Store full mapping of the model
    # We want to pass a dict to store_json_results_in_redis_and_s3, but the problem is account_mapping.dict()
    # includes pydantic objects that cannot be dumped to json without passing a special JSON encoder for the
    # Pydantic type, hence the usage of json.loads(account_mapping.json())
    await store_json_results_in_redis_and_s3(
        json.loads(account_mapping.json()),
        redis_key=redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        host=host,
    )

    return account_mapping


async def get_cloud_account_model_array(
    host, status="active", environment=None, force_sync=False
):
    redis_key = config.get_host_specific_key(
        f"site_configs.{host}.cache_cloud_accounts.redis.key.all_accounts_key",
        host,
        f"{host}_ALL_AWS_ACCOUNTS",
    )
    accounts = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        default={},
        host=host,
    )
    if force_sync or not accounts or not accounts.get("accounts"):
        # Force a re-sync and then retry
        await cache_cloud_accounts(host)
        accounts = await retrieve_json_data_from_redis_or_s3(
            redis_key,
            default={},
            host=host,
        )
    all_accounts = CloudAccountModelArray.parse_obj(accounts)
    filtered_accounts = CloudAccountModelArray(accounts=[])
    for account in all_accounts.accounts:
        if status and account.status.value != status:
            continue
        if environment and not account.environment:
            # if we are looking to filter on environment, and account doesn't contain environment information
            continue
        if environment and account.environment.value != environment:
            continue
        filtered_accounts.accounts.append(account)
    return filtered_accounts


async def get_account_id_to_name_mapping(
    host, status="active", environment=None, force_sync=False
):
    redis_key = config.get_host_specific_key(
        f"site_configs.{host}.cache_cloud_accounts.redis.key.all_accounts_key",
        host,
        f"{host}_ALL_AWS_ACCOUNTS",
    )
    accounts = await retrieve_json_data_from_redis_or_s3(
        redis_key, default={}, host=host
    )
    if force_sync or not accounts or not accounts.get("accounts"):
        # Force a re-sync and then retry
        await cache_cloud_accounts(host)
        accounts = await retrieve_json_data_from_redis_or_s3(
            redis_key,
            s3_bucket=config.get_host_specific_key(
                f"site_configs.{host}.cache_cloud_accounts.s3.bucket", host
            ),
            s3_key=config.get_host_specific_key(
                f"site_configs.{host}.cache_cloud_accounts.s3.file",
                host,
                "cache_cloud_accounts/accounts_v1.json.gz",
            ),
            default={},
            host=host,
        )

    account_id_to_name = {}
    for account in accounts.get("accounts", []):
        if status and account.get("status") != status:
            continue
        if environment and account.get("environment") != environment:
            continue
        account_id_to_name[account["id"]] = account["name"]
    return account_id_to_name
