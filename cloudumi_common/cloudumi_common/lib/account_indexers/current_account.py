from cloudumi_common.config import config
from cloudumi_common.lib.aws.session import get_session_for_tenant
from cloudumi_common.models import CloudAccountModel, CloudAccountModelArray


async def retrieve_current_account(host) -> CloudAccountModelArray:
    session = get_session_for_tenant(host)
    client = session.client(
        "sts", **config.get(f"site_configs.{host}.boto3.client_kwargs", {})
    )
    identity = client.get_caller_identity()
    account_aliases = session.client(
        "iam", **config.get(f"site_configs.{host}.boto3.client_kwargs", {})
    ).list_account_aliases()["AccountAliases"]
    account_id = None
    if identity and identity.get("Account"):
        account_id = identity.get("Account")
    account_name = account_id

    if account_aliases:
        account_name = account_aliases[0]

    cloud_account = [
        CloudAccountModel(
            id=account_id,
            name=account_name,
            status="active",
            sync_enabled=True,
            type="aws",
        )
    ]
    return CloudAccountModelArray(accounts=cloud_account)
