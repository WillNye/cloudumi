from typing import List

import sentry_sdk

from common.config import config
from common.handlers.base import BaseAPIV2Handler
from common.lib.generic import is_in_group
from common.lib.notifications.models import (
    ConsoleMeNotificationUpdateAction,
    ConsoleMeNotificationUpdateRequest,
    ConsoleMeUserNotification,
    GetNotificationsForUserResponse,
)
from common.lib.plugins import get_plugin_by_name
from common.lib.v2.notifications import (
    fetch_notification,
    get_notifications_for_user,
    write_notification,
)
from common.models import Status2, WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


class NotificationsHandler(BaseAPIV2Handler):
    """
    A web handler for serving, updating, and (in the future) creating notifications. Current notifications are based
    around policy generation from CloudTrail errors.
    """

    async def get(self):
        tenant = self.ctx.tenant
        try:
            max_notifications = config.get_tenant_specific_key(
                "get_notifications_for_user.max_notifications",
                tenant,
                5,
            )
            notification_response: GetNotificationsForUserResponse = (
                await get_notifications_for_user(
                    self.user, self.groups, tenant, max_notifications
                )
            )
            notifications: List[
                ConsoleMeUserNotification
            ] = notification_response.notifications
            response = WebResponse(
                status="success",
                status_code=200,
                data={
                    "unreadNotificationCount": notification_response.unread_count,
                    "notifications": notifications,
                },
            )
            self.write(response.json())
        except Exception as e:
            raise
            sentry_sdk.capture_exception()
            self.set_status(500)
            response = WebResponse(
                status=Status2.error, status_code=500, errors=[str(e)], data=[]
            )
            self.write(response.json())
            return

    async def post(self):
        # Create a notification
        raise NotImplementedError()

    async def put(self):
        """
        Allows an "authorized user" (Any user the notification is intended for) to mark the notification as read/unread
        or hidden/unhidden for themselves or all other notification recipients

        :return:
        """
        change = ConsoleMeNotificationUpdateRequest.parse_raw(self.request.body)
        errors = []

        tenant = self.ctx.tenant

        for untrusted_notification in change.notifications:
            notification = await fetch_notification(
                untrusted_notification.predictable_id, tenant
            )
            if not notification:
                errors.append("Unable to find matching notification")
                continue
            authorized = is_in_group(
                self.user, self.groups, notification.users_or_groups
            )
            if not authorized:
                errors.append(
                    f"Unauthorized because user is not associated with notification: {notification.predictable_id}"
                )
                continue
            if (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_read_for_current_user
            ):
                if self.user in notification.read_by_users:
                    # Mark as unread
                    notification.read_by_users.remove(self.user)
                else:
                    # Mark as read
                    notification.read_by_users.append(self.user)
            elif (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_read_for_all_users
            ):
                # Mark or unmark notification as `read_by_all`.  If unmarked,
                # ConsoleMe will fall back to `notification.read_by_user` to determine if
                # a given user has read the notification
                notification.read_by_all = not notification.read_by_all
            elif (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_hidden_for_current_user
            ):
                if self.user in notification.hidden_for_users:
                    # Unmark as hidden
                    notification.hidden_for_users.remove(self.user)
                else:
                    # Mark as hidden
                    notification.hidden_for_users.append(self.user)
            elif (
                change.action
                == ConsoleMeNotificationUpdateAction.toggle_hidden_for_all_users
            ):
                # Mark or unmark as "Hidden for all users". If unmarked, falls back to `hidden_for_users.read_by_user`
                # to determine whether to show the notification to a given user
                notification.hidden_for_all = not notification.hidden_for_all
            else:
                raise Exception("Unknown or unsupported change action.")
            await write_notification(notification, tenant)
        try:
            # Retrieve and return updated notifications for user
            max_notifications = config.get_tenant_specific_key(
                "get_notifications_for_user.max_notifications",
                tenant,
                5,
            )
            notification_response: GetNotificationsForUserResponse = (
                await get_notifications_for_user(
                    self.user,
                    self.groups,
                    tenant,
                    max_notifications,
                    force_refresh=True,
                )
            )
            notifications: List[
                ConsoleMeUserNotification
            ] = notification_response.notifications
            response = WebResponse(
                status="success",
                status_code=200,
                data={
                    "unreadNotificationCount": notification_response.unread_count,
                    "notifications": notifications,
                },
            )
            self.write(response.json())
        except Exception as e:
            raise
            sentry_sdk.capture_exception()
            self.set_status(500)
            response = WebResponse(
                status=Status2.error, status_code=500, errors=[str(e)], data=[]
            )
            self.write(response.json())
            return
