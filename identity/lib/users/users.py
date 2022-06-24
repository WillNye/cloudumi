import sys

import ujson as json

from common.config import config
from common.lib.cache import store_json_results_in_redis_and_s3
from common.lib.dynamo import UserDynamoHandler
from identity.lib.groups.models import OktaIdentityProvider, User
from identity.lib.groups.plugins.okta.plugin import OktaGroupManagementPlugin

log = config.get_logger()


def get_identity_user_storage_keys(tenant):
    s3_bucket = config.get_tenant_specific_key(
        "identity.cache_users.bucket",
        tenant,
        config.get("_global_.s3_cache_bucket"),
    )
    redis_key: str = config.get_tenant_specific_key(
        "identity.cache_users.redis_key",
        tenant,
        default=f"{tenant}_IDENTITY_USERS",
    )
    s3_key = config.get_tenant_specific_key(
        "identity.cache_users.key",
        tenant,
        default="identity/users/identity_users_cache_v1.json.gz",
    )
    return {
        "s3_bucket": s3_bucket,
        "redis_key": redis_key,
        "s3_key": s3_key,
    }


async def cache_identity_users_for_tenant(tenant):
    """
    Fetches all existing cached users for the tenant and determines which
    users to update or remove.

    Determines which identity providers are configured for the tenant,
    caches users for all configured identity providers, stores cached
    results in DynamoDB, S3, and Redis. Updates existing cache if
    necessary.

    :param tenant:
    :return:
    """
    # TODO: Only run in primary region
    # Check what identity providers are configured for tenant
    # Call "cache users" for all identity providers for a given tenant
    # Store results in DynamoDB, S3, and Redis
    # DynamoDB will also have our protected attributes about the user
    # So we can't blindly overwrite
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
    }
    enabled = config.get_tenant_specific_key("identity.cache_users.enabled", tenant)
    if not enabled:
        log.debug(
            {
                **log_data,
                "message": "Configuration key to enable user caching is not enabled for tenant.",
            }
        )
    ddb = UserDynamoHandler(tenant)
    existing_users = {}
    existing_users_l = ddb.fetch_users_for_tenant(tenant)["Items"]
    for user in existing_users_l:
        existing_users[user["username"]] = User.parse_obj(user)

    log_data["num_existing_users"] = len(existing_users)
    all_users = {}

    for idp_name, idp_d in config.get_tenant_specific_key(
        "identity.identity_providers", tenant, default={}
    ).items():
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(tenant, idp)
        else:
            raise Exception("IDP type is not supported.")
        refreshed_users = await idp_plugin.list_all_users()
        log_data["idp_name"] = idp_name
        log_data["num_detected_users"] = len(refreshed_users)
        users_to_update = {}
        users_to_remove = []
        for user in refreshed_users:
            users_to_update[user.user_id] = json.loads(user.json())
        all_users.update(users_to_update)
        log.debug({**log_data, "message": "Successfully pulled users from IDP"})

        # Remove users that we have cached for the IdP, but for which the IdP didn't remove
        for user_id, user in existing_users.items():
            if users_to_update.get(user_id):
                continue
            users_to_remove.append(
                {
                    "tenant": tenant,
                    "user_id": user_id,
                }
            )
        if users_to_update:
            ddb.parallel_write_table(
                ddb.identity_users_table,
                users_to_update.values(),
                ["tenant", "user_id"],
            )
        if users_to_remove:
            log.debug(
                {
                    **log_data,
                    "num_users_to_remove": len(users_to_remove),
                    "message": "Removing stale users from cache",
                }
            )
            ddb.parallel_delete_table_entries(ddb.identity_users_table, users_to_remove)

        await store_json_results_in_redis_and_s3(
            all_users, tenant=tenant, **get_identity_user_storage_keys(tenant)
        )


async def get_user_by_name(tenant, idp, user_name):
    """
    Gets a user by name from the cache.

    :param tenant:
    :param idp:
    :param user_name:
    :return:
    """
    user_id = f"{idp}-{user_name}"
    ddb = UserDynamoHandler(tenant)
    matching_user = ddb.identity_users_table.get_item(
        Key={"tenant": tenant, "user_id": user_id}
    )
    # if matching_group.get("Item"):
    if False:  # TODO: Remove
        return User.parse_obj(ddb._data_from_dynamo_replace(matching_user["Item"]))
    else:
        idp_d = config.get_tenant_specific_key(
            "identity.identity_providers", tenant, default={}
        ).get(idp)
        if not idp_d:
            raise Exception("Invalid IDP specified")
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(tenant, idp)
        else:
            raise Exception("IDP type is not supported.")
        return await idp_plugin.get_user(user_name)
