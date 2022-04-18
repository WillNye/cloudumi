import json as original_json
import sys
import time
from collections import defaultdict
from typing import Dict

import sentry_sdk
import ujson as json

from common.config import config
from common.lib.asyncio import aio_wrapper
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.dynamo import UserDynamoHandler
from common.lib.json_encoder import SetEncoder
from common.lib.notifications.models import (
    ConsoleMeUserNotification,
    GetNotificationsForUserResponse,
)
from common.lib.singleton import Singleton

log = config.get_logger()


class RetrieveNotifications(metaclass=Singleton):
    def __init__(self):
        self.last_update = 0
        self.all_notifications = []

    async def retrieve_all_notifications(self, host, force_refresh=False):
        if force_refresh or (
            int(time.time()) - self.last_update
            > config.get_host_specific_key(
                "get_notifications_for_user.notification_retrieval_interval",
                host,
                20,
            )
        ):
            self.all_notifications = await retrieve_json_data_from_redis_or_s3(
                redis_key=config.get_host_specific_key(
                    "notifications.redis_key",
                    host,
                    f"{host}_ALL_NOTIFICATIONS",
                ),
                redis_data_type="hash",
                s3_bucket=config.get_host_specific_key("notifications.s3.bucket", host),
                s3_key=config.get_host_specific_key(
                    "notifications.s3.key",
                    host,
                    "notifications/all_notifications_v1.json.gz",
                ),
                default={},
                host=host,
            )
            self.last_update = int(time.time())
        return self.all_notifications


async def get_notifications_for_user(
    user,
    groups,
    host,
    max_notifications,
    force_refresh=False,
) -> GetNotificationsForUserResponse:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "user": user,
        "max_notifications": max_notifications,
        "force_refresh": force_refresh,
        "host": host,
    }

    current_time = int(time.time())
    all_notifications = await RetrieveNotifications().retrieve_all_notifications(
        host, force_refresh=force_refresh
    )
    unread_count = 0
    notifications_for_user = []
    for user_or_group in [user, *groups]:
        # Filter out identical notifications that were already captured via user-specific attribution. IE: "UserA"
        # performed an access deny operation locally under "RoleA" with session name = "UserA", so the generated
        # notification is tied to the user. However, "UserA" is a member of "GroupA", which owns RoleA. We want
        # to show the notification to members of "GroupA", as well as "UserA" but we don't want "UserA" to see 2
        # notifications.
        notifications = all_notifications.get(user_or_group)
        if not notifications:
            continue
        notifications = json.loads(notifications)
        for notification_raw in notifications:
            try:
                # We parse ConsoleMeUserNotification individually instead of as an array
                # to account for future changes to the model that may invalidate older
                # notifications
                notification = ConsoleMeUserNotification.parse_obj(notification_raw)
            except Exception as e:
                log.error({**log_data, "error": str(e)})
                sentry_sdk.capture_exception()
                continue
            if notification.version != 1:
                # Skip unsupported versions of the notification model
                continue
            if user in notification.hidden_for_users:
                # Skip this notification if it isn't hidden for the user
                continue
            seen = False
            for existing_user_notification_raw in notifications_for_user:
                existing_user_notification = ConsoleMeUserNotification.parse_obj(
                    existing_user_notification_raw
                )
                if (
                    notification.predictable_id
                    == existing_user_notification.predictable_id
                ):
                    seen = True
            if not seen:
                notifications_for_user.append(notification)
    # Filter out "expired" notifications
    notifications_for_user = [
        v for v in notifications_for_user if v.expiration > current_time
    ]

    # Show newest notifications first
    notifications_for_user = sorted(
        notifications_for_user, key=lambda i: i.event_time, reverse=True
    )

    # Increment Unread Count
    notifications_to_return = notifications_for_user[0:max_notifications]
    for notification in notifications_to_return:
        if user in notification.read_by_users or notification.read_by_all:
            notification.read_for_current_user = True
            continue
        unread_count += 1
    return GetNotificationsForUserResponse(
        notifications=notifications_to_return, unread_count=unread_count
    )


async def fetch_notification(notification_id: str, host: str):
    ddb = UserDynamoHandler(host=host)
    notification = await aio_wrapper(
        ddb.notifications_table.get_item,
        Key={"host": host, "predictable_id": notification_id},
    )
    if notification.get("Item"):
        return ConsoleMeUserNotification.parse_obj(notification["Item"])


async def cache_notifications_to_redis_s3(host) -> Dict[str, int]:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    current_time = int(time.time())
    log_data = {"function": function}
    ddb = UserDynamoHandler(host=host)
    notifications_by_user_group = defaultdict(list)
    all_notifications_l = await ddb.parallel_scan_table_async(ddb.notifications_table)
    changed_notifications = []
    for existing_notification in all_notifications_l:
        notification = ConsoleMeUserNotification.parse_obj(existing_notification)
        if current_time > notification.expiration:
            notification.expired = True
            changed_notifications.append(notification.dict())
        for user_or_group in notification.users_or_groups:
            notifications_by_user_group[user_or_group].append(notification.dict())

    if changed_notifications:
        ddb.parallel_write_table(ddb.notifications_table, changed_notifications)

    if notifications_by_user_group:
        for k, v in notifications_by_user_group.items():
            notifications_by_user_group[k] = original_json.dumps(v, cls=SetEncoder)
        await store_json_results_in_redis_and_s3(
            notifications_by_user_group,
            redis_key=config.get_host_specific_key(
                "notifications.redis_key",
                host,
                f"{host}_ALL_NOTIFICATIONS",
            ),
            redis_data_type="hash",
            s3_bucket=config.get_host_specific_key("notifications.s3.bucket", host),
            s3_key=config.get_host_specific_key(
                "notifications.s3.key",
                host,
                "notifications/all_notifications_v1.json.gz",
            ),
            host=host,
        )
    log_data["num_user_groups_for_notifications"] = len(
        notifications_by_user_group.keys()
    )
    log_data["num_notifications"] = len(all_notifications_l)
    log.debug(log_data)
    return {
        "num_user_groups_to_notify": len(notifications_by_user_group.keys()),
        "num_notifications": len(all_notifications_l),
    }


async def write_notification(notification: ConsoleMeUserNotification, host):
    ddb = UserDynamoHandler(host=host)
    await aio_wrapper(
        ddb.notifications_table.put_item,
        Item=ddb._data_to_dynamo_replace(notification.dict()),
    )
    await cache_notifications_to_redis_s3(host)
    return True
