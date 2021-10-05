from cloudumi_common.config import config


def get_all_hosts():
    hosts = list(config.get("site_configs", {}).keys())
    return hosts
