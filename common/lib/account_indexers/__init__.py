import common.lib.noq_json as json
from common.config import config
from common.config.models import ModelAdapter
from common.lib.account_indexers.aws_organizations import (
    retrieve_accounts_from_aws_organizations,
)
from common.lib.account_indexers.local_config import retrieve_accounts_from_config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.plugins import get_plugin_by_name
from common.models import CloudAccountModelArray, SpokeAccount

log = config.get_logger(__name__)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent-bit"))()


async def cache_cloud_accounts(tenant) -> CloudAccountModelArray:
    """
    Gets Cloud Account Information from either Noq's configuration, AWS Organizations, or Swag,
    depending on configuration
    :return:
    """
    account_mapping = None
    # Get the accounts
    if config.get_tenant_specific_key(
        "cache_cloud_accounts.from_aws_organizations", tenant
    ):
        account_mapping = await retrieve_accounts_from_aws_organizations(tenant)
    elif config.get_tenant_specific_key(
        "cache_cloud_accounts.from_config", tenant, True
    ):
        account_mapping = await retrieve_accounts_from_config(tenant)

    account_id_to_name = {}

    for account in account_mapping.accounts:
        account_id_to_name[account.id] = account.name

    redis_key = config.get_tenant_specific_key(
        "cache_cloud_accounts.redis.key.all_accounts_key",
        tenant,
        f"{tenant}_ALL_AWS_ACCOUNTS",
    )

    s3_bucket = None
    s3_key = None
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment", None) in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "cache_cloud_accounts.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "cache_cloud_accounts.s3.file",
            tenant,
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
        tenant=tenant,
    )

    return account_mapping


async def get_cloud_account_model_array(
    tenant, status="active", environment=None, force_sync=False
):
    redis_key = config.get_tenant_specific_key(
        "cache_cloud_accounts.redis.key.all_accounts_key",
        tenant,
        f"{tenant}_ALL_AWS_ACCOUNTS",
    )
    accounts = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        default={},
        tenant=tenant,
    )
    if force_sync or not accounts or not accounts.get("accounts"):
        # Force a re-sync and then retry
        await cache_cloud_accounts(tenant)
        accounts = await retrieve_json_data_from_redis_or_s3(
            redis_key,
            default={},
            tenant=tenant,
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
    tenant, status="active", environment=None, force_sync=False
):
    accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant).models
    return {account.account_id: account.account_name for account in accounts}
