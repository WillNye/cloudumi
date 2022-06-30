from common.config import config
from common.lib.aws.session import get_session_for_tenant
from common.models import CloudAccountModel, CloudAccountModelArray


async def retrieve_current_account(tenant) -> CloudAccountModelArray:
    session = get_session_for_tenant(tenant)
    client = session.client(
        "sts",
        **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
    )
    identity = client.get_caller_identity()
    account_aliases = session.client(
        "iam",
        **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
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
