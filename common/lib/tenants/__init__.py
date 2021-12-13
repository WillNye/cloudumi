from typing import List

from config import config
from lib.dynamo import RestrictedDynamoHandler

ddb = RestrictedDynamoHandler()


def get_all_hosts() -> List[str]:
    hosts = ddb.get_all_hosts()
    hosts.extend(list(config.get("site_configs", {}).keys()))
    return list(set(hosts))
