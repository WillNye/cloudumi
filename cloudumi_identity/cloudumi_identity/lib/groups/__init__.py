import sys

from cloudumi_common.config import config
from cloudumi_common.lib.cache import store_json_results_in_redis_and_s3
from cloudumi_common.lib.dynamo import UserDynamoHandler
from cloudumi_identity.lib.groups.models import Group, OktaIdentityProvider
from cloudumi_identity.lib.groups.plugins.okta.plugin import OktaGroupManagementPlugin

log = config.get_logger()


def get_identity_group_storage_keys(host):
    s3_bucket = config.get_host_specific_key(
        f"site_configs.{host}.identity.cache_groups.bucket", host
    )
    redis_key: str = config.get_host_specific_key(
        f"site_configs.{host}.identity.cache_groups.redis_key",
        host,
        default=f"{host}_IDENTITY_GROUPS",
    )
    s3_key = config.get_host_specific_key(
        f"site_configs.{host}.identity.cache_groups.key",
        host,
        default="identity/groups/identity_groups_cache_v1.json.gz",
    )
    return {
        "s3_bucket": s3_bucket,
        "redis_key": redis_key,
        "s3_key": s3_key,
    }


async def cache_identity_groups_for_host(host):
    """
    Fetches all existing cached groups for the host and determines which
    groups to update or remove.

    Determines which identity providers are configured for the host,
    caches groups for all configured identity providers, stores cached
    results in DynamoDB, S3, and Redis. Updates existing cache if
    necessary.

    :param host:
    :return:
    """
    # TODO: Only run in primary region
    # Check what identity providers are configured for host
    # Call "cache groups" for all identity providers for a given host
    # Store results in DynamoDB, S3, and Redis
    # DynamoDB will also have our protected attributes about the group
    # So we can't blindly overwrite
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "host": host,
    }
    enabled = config.get_host_specific_key(
        f"site_configs.{host}.identity.cache_groups.enabled", host
    )
    if not enabled:
        log.debug(
            {
                **log_data,
                "message": "Configuration key to enable group caching is not enabled for host.",
            }
        )
    ddb = UserDynamoHandler(host)
    existing_groups = {}
    existing_groups_l = ddb.fetch_groups_for_host(host)["Items"]
    for group in existing_groups_l:
        existing_groups[group["group_id"]] = Group.parse_obj(group)

    log_data["num_existing_groups"] = len(existing_groups)
    all_groups = {}

    for idp_name, idp_d in config.get_host_specific_key(
        f"site_configs.{host}.identity.identity_providers", host, default={}
    ).items():
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(host, idp)
        else:
            raise Exception("IDP type is not supported.")
        refreshed_groups = await idp_plugin.list_all_groups()
        log_data["idp_name"] = idp_name
        log_data["num_detected_groups"] = len(refreshed_groups)
        groups_to_update = {}
        groups_to_remove = []
        for group_id, group in refreshed_groups.items():
            existing_group_d = existing_groups.get(group_id, {})
            if existing_group_d:
                existing_group = Group.parse_obj(existing_group_d)
                group.requestable = existing_group.requestable
                group.manager_approval_required = (
                    existing_group.manager_approval_required
                )
                group.approval_chain = existing_group.approval_chain
                group.self_approval_groups = existing_group.self_approval_groups
                group.allow_bulk_add_and_remove = (
                    existing_group.allow_bulk_add_and_remove
                )
                group.background_check_required = (
                    existing_group.background_check_required
                )
                group.allow_contractors = existing_group.allow_contractors
                group.allow_third_party = existing_group.allow_third_party
                group.emails_to_notify_on_new_members = (
                    existing_group.emails_to_notify_on_new_members
                )
            groups_to_update[group_id] = group.dict()
        all_groups.update(groups_to_update)
        log.debug({**log_data, "message": "Successfully pulled groups from IDP"})

        # Remove groups that we have cached for the Idp, but for which the IdP didn't remove
        for group_id, group in existing_groups.items():
            if groups_to_update.get(group_id):
                continue
            groups_to_remove.append(
                {
                    "host": host,
                    "group_id": group_id,
                }
            )
        if groups_to_update:
            ddb.parallel_write_table(
                ddb.identity_groups_table,
                groups_to_update.values(),
                ["host", "group_id"],
            )
        if groups_to_remove:
            log.debug(
                {
                    **log_data,
                    "num_groups_to_remove": len(groups_to_remove),
                    "message": "Removing stale groups from cache",
                }
            )
            ddb.parallel_delete_table_entries(
                ddb.identity_groups_table, groups_to_remove
            )

        await store_json_results_in_redis_and_s3(
            all_groups, host=host, **get_identity_group_storage_keys(host)
        )


import asyncio

asyncio.run(cache_identity_groups_for_host("localhost"))
