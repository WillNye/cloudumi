import sys

import ujson as json

from common.config import config
from common.lib.cache import store_json_results_in_redis_and_s3
from common.lib.dynamo import UserDynamoHandler
from identity.lib.groups.models import OktaIdentityProvider, User
from identity.lib.groups.plugins.okta.plugin import OktaGroupManagementPlugin

log = config.get_logger()


def get_identity_user_storage_keys(host):
    s3_bucket = config.get_host_specific_key(
        "identity.cache_users.bucket",
        host,
        config.get("_global_.s3_cache_bucket"),
    )
    redis_key: str = config.get_host_specific_key(
        "identity.cache_users.redis_key",
        host,
        default=f"{host}_IDENTITY_USERS",
    )
    s3_key = config.get_host_specific_key(
        "identity.cache_users.key",
        host,
        default="identity/users/identity_users_cache_v1.json.gz",
    )
    return {
        "s3_bucket": s3_bucket,
        "redis_key": redis_key,
        "s3_key": s3_key,
    }


async def cache_identity_users_for_host(host):
    """
    Fetches all existing cached users for the host and determines which
    users to update or remove.

    Determines which identity providers are configured for the host,
    caches users for all configured identity providers, stores cached
    results in DynamoDB, S3, and Redis. Updates existing cache if
    necessary.

    :param host:
    :return:
    """
    # TODO: Only run in primary region
    # Check what identity providers are configured for host
    # Call "cache users" for all identity providers for a given host
    # Store results in DynamoDB, S3, and Redis
    # DynamoDB will also have our protected attributes about the user
    # So we can't blindly overwrite
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "host": host,
    }
    enabled = config.get_host_specific_key("identity.cache_users.enabled", host)
    if not enabled:
        log.debug(
            {
                **log_data,
                "message": "Configuration key to enable user caching is not enabled for host.",
            }
        )
    ddb = UserDynamoHandler(host)
    existing_users = {}
    existing_users_l = ddb.fetch_users_for_host(host)["Items"]
    for user in existing_users_l:
        existing_users[user["username"]] = User.parse_obj(user)

    log_data["num_existing_users"] = len(existing_users)
    all_users = {}

    for idp_name, idp_d in config.get_host_specific_key(
        "identity.identity_providers", host, default={}
    ).items():
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(host, idp)
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
                    "host": host,
                    "user_id": user_id,
                }
            )
        if users_to_update:
            ddb.parallel_write_table(
                ddb.identity_users_table,
                users_to_update.values(),
                ["host", "user_id"],
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
            all_users, host=host, **get_identity_user_storage_keys(host)
        )


async def get_user_by_name(host, idp, user_name):
    """
    Gets a user by name from the cache.

    :param host:
    :param idp:
    :param user_name:
    :return:
    """
    user_id = f"{idp}-{user_name}"
    ddb = UserDynamoHandler(host)
    matching_user = ddb.identity_users_table.get_item(
        Key={"host": host, "user_id": user_id}
    )
    # if matching_group.get("Item"):
    if False:  # TODO: Remove
        return User.parse_obj(ddb._data_from_dynamo_replace(matching_user["Item"]))
    else:
        idp_d = config.get_host_specific_key(
            "identity.identity_providers", host, default={}
        ).get(idp)
        if not idp_d:
            raise Exception("Invalid IDP specified")
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(host, idp)
        else:
            raise Exception("IDP type is not supported.")
        return await idp_plugin.get_user(user_name)
