import sys
from typing import List

import sentry_sdk

from common.config import config
from common.lib.cache import store_json_results_in_redis_and_s3
from common.lib.dynamo import UserDynamoHandler
from common.lib.s3_helpers import get_s3_bucket_for_tenant
from identity.lib.groups.models import Group, OktaIdentityProvider, User
from identity.lib.groups.plugins.okta.plugin import OktaGroupManagementPlugin

log = config.get_logger(__name__)


async def get_identity_provider_plugin(tenant: str, idp_name: str):
    idp_d = config.get_tenant_specific_key(
        "identity.identity_providers", tenant, default={}
    ).get(idp_name)
    if not idp_d:
        raise Exception("Invalid IDP specified")
    if idp_d["idp_type"] == "okta":
        idp = OktaIdentityProvider.parse_obj(idp_d)
        return OktaGroupManagementPlugin(tenant, idp)
    raise Exception("Invalid IDP name specified")


async def add_users_to_groups(
    tenant, users: List[User], groups: List[Group], actor: str
):
    """
    Add users to groups. all users and groups must be from the same IdP
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
        "actor": actor,
        "users": [user.username for user in users],
        "groups": [group.name for group in groups],
    }
    log.debug(log_data)
    errors = []
    for user in users:
        for group in groups:
            if user.idp_name != group.idp_name:
                raise Exception("User and group must be from the same IDP")
            try:
                await add_user_to_group(tenant, user, group, actor)
            except Exception as e:
                errors.append(
                    f"{user.username} could not be added to {group.name}: {e}"
                )
                sentry_sdk.capture_exception()
    return errors


async def add_user_to_group(tenant, user: User, group: Group, actor: str):
    """
    Add user to group
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
        "user": user.username,
        "actor": actor,
        "group": group.name,
    }
    log.debug(log_data)
    if user.idp_name != group.idp_name:
        raise Exception("User and group must be from the same IDP")
    idp_plugin = await get_identity_provider_plugin(tenant, group.idp_name)
    return await idp_plugin.add_user_to_group(user, group, actor)


def get_identity_request_storage_keys(tenant):
    s3_bucket = config.get_tenant_specific_key(
        "identity.cache_requests.bucket",
        tenant,
        config.get("_global_.s3_cache_bucket"),
    )
    redis_key: str = config.get_tenant_specific_key(
        "identity.cache_requests.redis_key",
        tenant,
        default=f"{tenant}_IDENTITY_REQUESTS",
    )
    s3_key = config.get_tenant_specific_key(
        "identity.cache_requests.key",
        tenant,
        default="identity/requests/identity_requests_cache_v1.json.gz",
    )
    return {
        "s3_bucket": s3_bucket,
        "redis_key": redis_key,
        "s3_key": s3_key,
    }


def get_identity_group_storage_keys(tenant):
    s3_bucket = config.get_tenant_specific_key(
        "identity.cache_groups.bucket",
        tenant,
        config.get("_global_.s3_cache_bucket"),
    )
    redis_key: str = config.get_tenant_specific_key(
        "identity.cache_groups.redis_key",
        tenant,
        default=f"{tenant}_IDENTITY_GROUPS",
    )
    s3_key = config.get_tenant_specific_key(
        "identity.cache_groups.key",
        tenant,
        default="identity/groups/identity_groups_cache_v1.json.gz",
    )
    return {
        "s3_bucket": s3_bucket,
        "redis_key": redis_key,
        "s3_key": s3_key,
    }


async def cache_identity_requests_for_tenant(tenant):
    """
    Cache all group requests for tenant
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
    }
    # Get group requests from Dynamo
    ddb = UserDynamoHandler(tenant)
    group_requests = await ddb.get_all_identity_group_requests(tenant)
    group_requests_by_id = {}
    for req in group_requests:
        group_requests_by_id[req["request_id"]] = req
    log_data["len_group_requests"] = len(group_requests)
    #  Store in Redis/S3
    red_key = f"{tenant}_IDENTITY_REQUESTS"
    await store_json_results_in_redis_and_s3(
        group_requests_by_id,
        redis_key=red_key,
        s3_bucket=await get_s3_bucket_for_tenant(tenant),
        tenant=tenant,
    )
    log.debug({**log_data, "message": "Cached identity requests"})


async def cache_identity_groups_for_tenant(tenant):
    """
    Fetches all existing cached groups for the tenant and determines which
    groups to update or remove.

    Determines which identity providers are configured for the tenant,
    caches groups for all configured identity providers, stores cached
    results in DynamoDB, S3, and Redis. Updates existing cache if
    necessary.

    :param tenant:
    :return:
    """
    # TODO: Only run in primary region
    # Check what identity providers are configured for tenant
    # Call "cache groups" for all identity providers for a given tenant
    # Store results in DynamoDB, S3, and Redis
    # DynamoDB will also have our protected attributes about the group
    # So we can't blindly overwrite
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
    }
    enabled = config.get_tenant_specific_key("identity.cache_groups.enabled", tenant)
    if not enabled:
        log.debug(
            {
                **log_data,
                "message": "Configuration key to enable group caching is not enabled for tenant.",
            }
        )
    ddb = UserDynamoHandler(tenant)
    existing_groups = {}
    existing_groups_l = ddb.fetch_groups_for_tenant(tenant)["Items"]
    for group in existing_groups_l:
        existing_groups[group["group_id"]] = Group.parse_obj(group)

    log_data["num_existing_groups"] = len(existing_groups)
    all_groups = {}

    for idp_name, idp_d in config.get_tenant_specific_key(
        "identity.identity_providers", tenant, default={}
    ).items():
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(tenant, idp)
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
                group.attributes = existing_group.attributes
                # group.requestable = existing_group.attributes.requestable
                # group.manager_approval_required = (
                #     existing_group.attributes.manager_approval_required
                # )
                # group.approval_chain = existing_group.attributes.approval_chain
                # group.self_approval_groups = existing_group.attributes.self_approval_groups
                # group.allow_bulk_add_and_remove = (
                #     existing_group.attributes.allow_bulk_add_and_remove
                # )
                # group.background_check_required = (
                #     existing_group.attributes.background_check_required
                # )
                # group.allow_contractors = existing_group.attributes.allow_contractors
                # group.allow_third_party = existing_group.attributes.allow_third_party
                # group.emails_to_notify_on_new_members = (
                #     existing_group.attributes.emails_to_notify_on_new_members
                # )
            groups_to_update[group_id] = group.dict()
        all_groups.update(groups_to_update)
        log.debug({**log_data, "message": "Successfully pulled groups from IDP"})

        # Remove groups that we have cached for the Idp, but for which the IdP didn't remove
        for group_id, group in existing_groups.items():
            if groups_to_update.get(group_id):
                continue
            groups_to_remove.append(
                {
                    "tenant": tenant,
                    "group_id": group_id,
                }
            )
        if groups_to_update:
            ddb.parallel_write_table(
                ddb.identity_groups_table,
                groups_to_update.values(),
                ["tenant", "group_id"],
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
            all_groups, tenant=tenant, **get_identity_group_storage_keys(tenant)
        )


async def get_group_by_name(tenant, idp, group_name):
    """
    Gets a group from the cache.

    :param tenant:
    :param group_id:
    :return:
    """
    group_id = f"{idp}-{group_name}"
    ddb = UserDynamoHandler(tenant)

    matching_group = None
    matching_group_item = ddb.identity_groups_table.get_item(
        Key={"tenant": tenant, "group_id": group_id}
    )
    if matching_group_item.get("Item"):
        matching_group = Group.parse_obj(matching_group_item["Item"])
    if False:  # TODO: Remove
        return Group.parse_obj(ddb._data_from_dynamo_replace(matching_group["Item"]))
    else:
        idp_plugin = await get_identity_provider_plugin(tenant, idp)
        group = await idp_plugin.get_group(group_name)
        if matching_group:
            group.attributes = matching_group.attributes
        return matching_group
