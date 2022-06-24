from typing import List

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler

ddb = RestrictedDynamoHandler()


def get_all_tenants() -> List[str]:
    tenants = ddb.get_all_tenants()
    tenants.extend(list(config.get("site_configs", {}).keys()))
    return list(set(tenants))
