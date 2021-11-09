import tornado.escape
import ujson as json
from cloudumi_identity.lib.groups.groups import get_group_by_name
from cloudumi_identity.lib.groups.models import GroupRequestsTable
from cloudumi_identity.lib.requests import get_request_by_id, request_access_to_group

from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseHandler
from cloudumi_common.lib.auth import can_admin_identity
from cloudumi_common.models import Status2, WebResponse

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
        # Is user authorized to make changes to this request?
        if not can_admin_identity(self.user, self.groups, host):
            log.error(log_data)
            res = WebResponse(status=Status2.error, message="Not authorized.")
            self.set_status(401)
            self.write(json.loads(res.json()))
            return

        # TODO: Handle approval and rejection of request
        # TODO: Handle adding to group with expiration if provided


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
