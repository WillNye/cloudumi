import tornado.escape
import ujson as json
from identity.lib.groups.groups import add_users_to_groups, get_group_by_name
from identity.lib.groups.models import Group, GroupRequestsTable, User
from identity.lib.requests import (
    approve_group_request,
    cancel_group_request,
    get_request_by_id,
    request_access_to_group,
)

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_identity
from common.models import Status2, WebResponse

log = config.get_logger()


class IdentityGroupRequestReviewHandler(BaseHandler):
    async def get(self, request_id):
        host = self.ctx.host
        log_data = {
            "function": "IdentityGroupHandler.get",
            "user": self.user,
            "message": "Retrieving group request information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "identity_request_id": request_id,
            "host": host,
        }
        # Get request from DynamoDB
        request = await get_request_by_id(host, request_id)
        if not request:
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="No request found.")
            self.set_status(400)
            self.write(json.loads(res.json()))
            return

        # TODO: Let user view full request JSON
        # TODO: Tell user if they are allowed to approve or cancel the request

        requests_table = GroupRequestsTable.parse_obj(
            {
                "User": ", ".join(
                    user.username for user in request.users
                ),  # TODO: Should be Markdown link to users profile
                "Group": ", ".join(
                    group.name for group in request.groups
                ),  # TODO: Markdown link
                "Requester": request.requester.username,  # TODO: Markdown link
                "Justification": request.justification,
                "Expires": request.expires or "Never",
                "Status": request.status.value,
                "LastUpdated": request.last_updated[
                    -1
                ].time,  # TODO: Convert to friendly datetime
            }
        )

        data = {
            "requests_table": json.loads(requests_table.json()),
            "request": json.loads(request.json()),
        }

        res = WebResponse(status=Status2.success, data=data)
        self.write(json.loads(res.json()))

    async def post(self, request_id):
        host = self.ctx.host
        # TODO: Format data into a model
        data = tornado.escape.json_decode(self.request.body)

        log_data = {
            "function": "IdentityGroupHandler.get",
            "user": self.user,
            "message": "Retrieving group request information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "identity_request_id": request_id,
            "host": host,
        }
        # Get request from DynamoDB
        request = await get_request_by_id(host, request_id)
        if not request:
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="No request found.")
            self.set_status(400)
            self.write(json.loads(res.json(exclude_unset=True)))
            return
        # Is user authorized to make changes to this request?
        if not can_admin_identity(self.user, self.groups, host):
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="Not authorized.")
            self.set_status(401)
            self.write(json.loads(res.json(exclude_unset=True)))
            return

        # TODO: Support admins re-open closed request

        if request.status.value != "pending":
            log.error(log_data)
            res = WebResponse(
                status=Status2.error, message="Request has already been actioned."
            )
            self.set_status(400)
            self.write(json.loads(res.json(exclude_unset=True)))
            return

        # Check current request status
        if request.status.value == data["action"]:
            log.error(log_data)
            res = WebResponse(
                status=Status2.error,
                message=f"Request is already {request.status.value}.",
            )
            self.set_status(400)
            self.write(json.loads(res.json(exclude_unset=True)))
            return

        if data["action"] == "approved":
            res = await approve_group_request(host, request, self.user, data["comment"])
            self.write(
                WebResponse(
                    status=Status2.success,
                    status_code=200,
                    message="Group request approved, and user added to group.",
                ).json(exclude_unset=True)
            )
        elif data["action"] == "cancelled":
            # TODO: Handle cancellation of request
            res = await cancel_group_request(host, request, self.user, data["comment"])
            self.write(
                WebResponse(
                    status=Status2.success,
                    status_code=200,
                    message="Group request cancelled.",
                ).json(exclude_unset=True)
            )
        else:
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="Invalid action.")
            self.set_status(400)
            self.write(json.loads(res.json(exclude_unset=True)))
            return

        # TODO: Handle adding to group with expiration if provided


class IdentityRequestGroupsHandler(BaseHandler):
    async def post(self):
        host = self.ctx.host
        data = tornado.escape.json_decode(self.request.body)

        log_data = {
            "function": "IdentityGroupHandler.get",
            "user": self.user,
            "message": "Retrieving group information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        user = data["user"]
        justification = data["justification"]
        group_expiration = data["groupExpiration"]
        bulk_group_edit_field = data["bulkGroupEditField"]
        idp_name = data["idpName"]

        groups_str = bulk_group_edit_field.replace("\n", ",")
        groups_str = groups_str.replace(" ", "")
        groups = groups_str.split(",")

        if not justification:
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="No justification provided")
            self.set_status(400)
            self.write(json.loads(res.json()))
            return

        # TODO: Allow non-admins to "request" access instead of auto-approving and bulk adding
        if not can_admin_identity(self.user, self.groups, host):
            log.error(log_data)
            res = WebResponse(
                status=Status2.error, message="Not authorized to admin identity."
            )
            self.set_status(401)
            self.write(json.loads(res.json()))
            return

        if not idp_name:
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="No idp name provided")
            self.set_status(400)
            self.write(json.loads(res.json()))
            return

        user_obj = [
            User(
                idp_name=idp_name,
                username=user,
                host=host,
            )
        ]

        groups = [Group(name=group, host=host, idp_name=idp_name) for group in groups]
        # TODO: Support group expiration in bulk-addition group requests
        await add_users_to_groups(host, user_obj, groups, justification)

        # request = await request_access_to_group(
        #     host,
        #     user,
        #     self.user,
        #     self.groups,
        #     idp_name,
        #     groups,
        #     justification,
        #     group_expiration,
        # )

        log.debug(log_data)

        res = WebResponse(
            status=Status2.success,
            message=f"Successfully added user to groups",
        )
        self.write(json.loads(res.json()))


class IdentityRequestGroupHandler(BaseHandler):
    async def get(self, _idp, _group_name):
        """
        Returns information needed to render the Request Groups page.
        :return:
        """
        host = self.ctx.host
        log_data = {
            "function": "IdentityGroupHandler.get",
            "user": self.user,
            "message": "Retrieving group information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "idp": _idp,
            "group_name": _group_name,
            "host": host,
        }
        log.debug(log_data)

    async def post(self, _idp, _group_names):
        """
        Request access to a group
        :return:
        """
        host = self.ctx.host
        log_data = {
            "function": "IdentityGroupHandler.get",
            "user": self.user,
            "message": "Retrieving group information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "idp": _idp,
            "group_name": _group_names,
            "host": host,
        }

        data = tornado.escape.json_decode(self.request.body)
        justification = data["justification"]
        group_expiration = data["groupExpiration"]
        user = data.get("user") or self.user

        if not justification:
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="No justification provided")
            self.set_status(400)
            self.write(json.loads(res.json()))
            return

        request = await request_access_to_group(
            host,
            user,
            self.user,
            self.groups,
            _idp,
            _group_names,
            justification,
            group_expiration,
        )

        # TODO: Call library to store request in DynamoDB ; Trigger Slack/Email notification somewhere?
        # Trigger update of group requests cache
        log.debug(log_data)

        res = WebResponse(
            status=Status2.success,
            message=f"Successfully created request. View it [here]({request.request_url})",
        )
        self.write(json.loads(res.json()))
