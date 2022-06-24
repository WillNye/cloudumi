from common.config import config
from common.models import CloudAccountModel, CloudAccountModelArray


async def retrieve_accounts_from_config(tenant) -> CloudAccountModelArray:
    cloud_accounts = []
    accounts_in_configuration = config.get_tenant_specific_key(
        "dynamic_config.account_ids_to_name", tenant, {}
    )
    accounts_in_configuration.update(
        config.get_tenant_specific_key("account_ids_to_name", tenant, {})
    )
    for account_id, names in accounts_in_configuration.items():
        account_name = names
        # Legacy support for a list of account names (with aliases)
        if account_name and isinstance(account_name, list):
            account_name = account_name[0]
        cloud_accounts.append(
            CloudAccountModel(
                id=account_id,
                name=account_name,
                status="active",
                sync_enabled=True,
                type="aws",
            )
        )
    return CloudAccountModelArray(accounts=cloud_accounts)
