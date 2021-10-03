import boto3

from cloudumi_common.config import config


def get_session_for_tenant(host, region_name=config.region):
    """
    Allows specifying a session with custom kwargs depending on the tenant
    """
    session_kwargs = config.get(f"site_configs.{host}.boto3.session_kwargs", {})
    session_kwargs["region_name"] = region_name
    session = boto3.Session(**session_kwargs)
    return session
