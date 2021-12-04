import boto3

from common.config import config


def get_session_for_tenant(host, region_name=config.region):
    """
    Allows specifying a session with custom kwargs depending on the tenant
    """
    session_kwargs = config.get_host_specific_key(
        f"site_configs.{host}.boto3.session_kwargs", host, {}
    )
    session_kwargs["region_name"] = region_name
    session = boto3.Session(**session_kwargs)
    return session


def restricted_get_session_for_saas(region_name=config.region):
    """
    Allows specifying a session with custom kwargs for the SaaS
    """
    session_kwargs = config.get("_global_.boto3.session_kwargs", {})
    session_kwargs["region_name"] = region_name
    session = boto3.Session(**session_kwargs)
    return session
