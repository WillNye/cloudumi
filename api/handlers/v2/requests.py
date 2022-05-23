import asyncio
import sys
import time
import uuid

import sentry_sdk
import ujson as json
from policy_sentry.util.arns import parse_arn
from pydantic import ValidationError

from common.aws.iam.role.models import IAMRole
from common.config import config
from common.exceptions.exceptions import (
    InvalidRequestParameter,
    MustBeFte,
    NoMatchingRequest,
    ResourceNotFound,
    Unauthorized,
)
from common.handlers.base import BaseAPIV2Handler, BaseHandler
from common.lib.asyncio import aio_wrapper
from common.lib.auth import (
    can_admin_policies,
    get_extended_request_account_ids,
    populate_approve_reject_policy,
)
from common.lib.aws.cached_resources.iam import get_tear_supported_roles_by_tag
from common.lib.aws.utils import get_resource_account
from common.lib.generic import filter_table, write_json_error
from common.lib.mfa import mfa_verify
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import (
    can_move_back_to_pending_v2,
    can_update_cancel_requests_v2,
    get_url_for_resource,
    should_auto_approve_policy_v2,
)
from common.lib.slack import send_slack_notification_new_request
from common.lib.timeout import Timeout
from common.lib.v2.requests import (
    generate_request_from_change_model_array,
    get_request_url,
    is_request_eligible_for_auto_approval,
    parse_and_apply_policy_request_modification,
    populate_cross_account_resource_policies,
    populate_old_managed_policies,
    populate_old_policies,
)
from common.models import (
    CommentModel,
    DataTableResponse,
    ExtendedRequestModel,
    PolicyRequestModificationRequestModel,
    RequestCreationModel,
    RequestCreationResponse,
    RequestStatus,
)
from common.models import Status2 as WebStatus
from common.models import WebResponse
from common.user_request.models import IAMRequest

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


async def validate_request_creation(
    handler, request: RequestCreationModel
) -> RequestCreationModel:
    err = ""

    if tear_change := next(
        (c for c in request.changes.changes if c.change_type == "tear_can_assume_role"),
        None,
    ):
        tear_supported_roles = await get_tear_supported_roles_by_tag(
            handler.eligible_roles, handler.groups, handler.ctx.host
        )
        tear_supported_roles = [role["arn"] for role in tear_supported_roles]

        if (
            not tear_supported_roles
            or tear_change.principal.principal_arn not in tear_supported_roles
        ):
            err += f"No TEAR support for {tear_change.principal.principal_arn} or access already exists. "

        if not request.expiration_date:
            err += "expiration_date is a required field for temporary elevated access requests. "

        if err:
            handler.set_status(400)
            handler.write(
                WebResponse(staus=WebStatus.error, errors=[err]).json(
                    exclude_unset=True, exclude_none=True
                )
            )
            return await handler.finish()

        is_authenticated, err = await mfa_verify(handler.ctx.host, handler.user)
        if not is_authenticated:
            handler.set_status(403)
            handler.write(
                WebResponse(staus=WebStatus.error, errors=[err]).json(
                    exclude_unset=True, exclude_none=True
                )
            )
            return await handler.finish()

        request.admin_auto_approve = False

    return request


class RequestHandler(BaseAPIV2Handler):
    """Handler for /api/v2/request

    Allows for creation of a request.
    """

    allowed_methods = ["POST"]

    def on_finish(self) -> None:
        if self.request.method != "POST":
            return
        from common.celery_tasks.celery_tasks import app as celery_app

        host = self.ctx.host
        try:
            with Timeout(
                seconds=5, error_message="Timeout: Are you sure Celery is running?"
            ):
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
                    kwargs={"host": host},
                )
        except TimeoutError:
            sentry_sdk.capture_exception()

    async def post(self):
        """
        POST /api/v2/request

        Request example JSON: (Request Schema is RequestCreationModel in models.py)

        {
          "changes": {
            "changes": [
              {
                "principal": {
                    "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                    "principal_type": "AwsResource"
                },
                "change_type": "inline_policy",
                "action": "attach",
                "policy": {
                  "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                      {
                        "Action": [
                          "s3:ListMultipartUploadParts*",
                          "s3:ListBucket"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "arn:aws:s3:::curtis-nflx-test/*",
                          "arn:aws:s3:::curtis-nflx-test"
                        ],
                        "Sid": "cmccastrapel159494014dsd1shak"
                      },
                      {
                        "Action": [
                          "ec2:describevolumes",
                          "ec2:detachvolume",
                          "ec2:describelicenses",
                          "ec2:AssignIpv6Addresses",
                          "ec2:reportinstancestatus"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "*"
                        ],
                        "Sid": "cmccastrapel1594940141hlvvv"
                      },
                      {
                        "Action": [
                          "sts:AssumeRole"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "arn:aws:iam::123456789012:role/curtisTestInstanceProfile"
                        ],
                        "Sid": "cmccastrapel1596483596easdits"
                      }
                    ]
                  }
                }
              },
              {
                "principal": {
                    "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                    "principal_type": "AwsResource"
                },
                "change_type": "assume_role_policy",
                "policy": {
                  "policy_document": {
                    "Statement": [
                      {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                          "AWS": "arn:aws:iam::123456789012:role/testInstanceProfile"
                        },
                        "Sid": "AllowConsoleMeProdAssumeRoles"
                      }
                    ],
                    "Version": "2012-10-17"
                  }
                }
              },
              {
                "principal": {
                    "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                    "principal_type": "AwsResource"
                },
                "change_type": "managed_policy",
                "policy_name": "ApiProtect",
                "action": "attach",
                "arn": "arn:aws:iam::123456789012:policy/ApiProtect"
              },
              {
                "principal": {
                    "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                    "principal_type": "AwsResource"
                },
                "change_type": "managed_policy",
                "policy_name": "TagProtect",
                "action": "detach",
                "arn": "arn:aws:iam::123456789012:policy/TagProtect"
              },
              {
                "principal": {
                    "principal_arn": "arn:aws:iam::123456789012:role/curtisTestRole1",
                    "principal_type": "AwsResource"
                },
                "change_type": "inline_policy",
                "policy_name": "random_policy254",
                "action": "attach",
                "policy": {
                  "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                      {
                        "Action": [
                          "ec2:AssignIpv6Addresses"
                        ],
                        "Effect": "Allow",
                        "Resource": [
                          "*"
                        ],
                        "Sid": "cmccastrapel1594940141shakabcd"
                      }
                    ]
                  }
                }
              }
            ]
          },
          "justification": "testing this out.",
          "admin_auto_approve": false
        }

        Response example JSON: (Response Schema is RequestCreationResponse in models.py)

        {
            "errors": 1,
            "request_created": true,
            "request_id": "0c9fb298-c8ea-4d50-917c-3212da07b3ad",
            "action_results": [
                {
                    "status": "success",
                    "message": "Success description"
                },
                {
                    "status": "error",
                    "message": "Error description"
                }
            ]
        }


        """
        host = self.ctx.host
        if (
            config.get_host_specific_key(
                "policy_editor.disallow_contractors", host, True
            )
            and self.contractor
        ):
            if self.user not in config.get_host_specific_key(
                "groups.can_bypass_contractor_restrictions",
                host,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        tags = {
            "user": self.user,
            "host": host,
        }
        stats.count("RequestHandler.post", tags=tags)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Create request initialization",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "admin_auto_approved": False,
            "probe_auto_approved": False,
            "host": host,
        }
        aws = get_plugin_by_name(
            config.get_host_specific_key("plugins.aws", host, "cmsaas_aws")
        )()
        log.debug(log_data)
        try:
            # Validate the model
            changes = RequestCreationModel.parse_raw(self.request.body)
            if not changes.dry_run:
                changes = await validate_request_creation(self, changes)

            extended_request = await generate_request_from_change_model_array(
                changes, self.user, host
            )
            log_data["request"] = extended_request.dict()
            log.debug(log_data)

            if changes.dry_run:
                response = RequestCreationResponse(
                    errors=0, request_created=False, extended_request=extended_request
                )
                self.write(response.json())
                await self.finish()
                return

            admin_approved = False
            approval_probe_approved = False

            if extended_request.principal.principal_type == "AwsResource":
                # TODO: Provide a note to the requester that admin_auto_approve will apply the requested policies only.
                # It will not automatically apply generated policies. The administrative user will need to visit
                # the policy request page to do this manually.
                if changes.admin_auto_approve:
                    # make sure user is allowed to use admin_auto_approve
                    account_ids = await get_extended_request_account_ids(
                        extended_request, host
                    )
                    can_manage_policy_request = (
                        await can_admin_policies(
                            self.user, self.groups, host, account_ids
                        ),
                    )
                    if can_manage_policy_request:
                        extended_request.request_status = RequestStatus.approved
                        admin_approved = True
                        extended_request.reviewer = self.user
                        self_approval_comment = CommentModel(
                            id=str(uuid.uuid4()),
                            timestamp=int(time.time()),
                            user_email=self.user,
                            user=extended_request.requester_info,
                            last_modified=int(time.time()),
                            text=f"Self-approved by admin: {self.user}",
                        )
                        extended_request.comments.append(self_approval_comment)
                        log_data["admin_auto_approved"] = True
                        log_data["request"] = extended_request.dict()
                        log.debug(log_data)
                        stats.count(
                            f"{log_data['function']}.post.admin_auto_approved",
                            tags={
                                "user": self.user,
                                "host": host,
                            },
                        )
                    else:
                        # someone is trying to use admin bypass without being an admin, don't allow request to proceed
                        stats.count(
                            f"{log_data['function']}.post.unauthorized_admin_bypass",
                            tags={
                                "user": self.user,
                                "host": host,
                            },
                        )
                        log_data[
                            "message"
                        ] = "Unauthorized user trying to use admin bypass"
                        log.error(log_data)
                        await write_json_error("Unauthorized", obj=self)
                        return
                else:
                    # If admin auto approve is false, check for auto-approve probe eligibility
                    is_eligible_for_auto_approve_probe = (
                        await is_request_eligible_for_auto_approval(
                            extended_request, self.user
                        )
                    )
                    # If we have only made requests that are eligible for auto-approval probe, check against them
                    if is_eligible_for_auto_approve_probe:
                        should_auto_approve_request = (
                            await should_auto_approve_policy_v2(
                                extended_request, self.user, self.groups, host
                            )
                        )
                        if should_auto_approve_request["approved"]:
                            extended_request.request_status = RequestStatus.approved
                            approval_probe_approved = True
                            stats.count(
                                f"{log_data['function']}.probe_auto_approved",
                                tags={
                                    "user": self.user,
                                    "host": host,
                                },
                            )
                            approving_probes = []
                            for approving_probe in should_auto_approve_request[
                                "approving_probes"
                            ]:
                                approving_probe_comment = CommentModel(
                                    id=str(uuid.uuid4()),
                                    timestamp=int(time.time()),
                                    user_email=f"Auto-Approve Probe: {approving_probe['name']}",
                                    last_modified=int(time.time()),
                                    text=(
                                        f"Policy {approving_probe['policy']} auto-approved by probe: "
                                        f"{approving_probe['name']}"
                                    ),
                                )
                                extended_request.comments.append(
                                    approving_probe_comment
                                )
                                approving_probes.append(approving_probe["name"])
                            extended_request.reviewer = (
                                f"Auto-Approve Probe: {','.join(approving_probes)}"
                            )
                            log_data["probe_auto_approved"] = True
                            log_data["request"] = extended_request.dict()
                            log.debug(log_data)

            request = await IAMRequest.write_v2(extended_request, host)
            log_data["message"] = "New request created in Dynamo"
            log_data["request"] = extended_request.dict()
            log_data["dynamo_request"] = request.dict()
            log.debug(log_data)
        except (InvalidRequestParameter, ValidationError) as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception",
                tags={
                    "user": self.user,
                    "host": host,
                },
            )
            self.write_error(400, message="Error validating input: " + str(e))
            if config.get("_global_.development"):
                raise
            return
        except Exception as e:
            log_data["message"] = "Unknown Exception occurred while parsing request"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "host": host,
                },
            )
            sentry_sdk.capture_exception(tags={"user": self.user})
            self.write_error(500, message="Error parsing request: " + str(e))
            if config.get("_global_.development"):
                raise
            return

        request_url = await get_request_url(extended_request)

        # If here, request has been successfully created
        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            request_url=request_url,
            action_results=[],
            extended_request=extended_request,
        )

        # If approved is true due to an auto-approval probe or admin auto-approval, apply the non-autogenerated changes
        if extended_request.request_status == RequestStatus.approved:
            for change in extended_request.changes.changes:
                if change.autogenerated:
                    continue
                policy_request_modification_model = (
                    PolicyRequestModificationRequestModel.parse_obj(
                        {
                            "modification_model": {
                                "command": "apply_change",
                                "change_id": change.id,
                            }
                        }
                    )
                )
                policy_apply_response = (
                    await parse_and_apply_policy_request_modification(
                        extended_request,
                        policy_request_modification_model,
                        self.user,
                        self.groups,
                        int(time.time()),
                        host,
                        approval_probe_approved=approval_probe_approved,
                    )
                )
                response.errors = policy_apply_response.errors
                response.action_results = policy_apply_response.action_results

            # Update in dynamo
            await IAMRequest.write_v2(extended_request, host)
            account_id = await get_resource_account(
                extended_request.principal.principal_arn, host
            )

            # Force a refresh of the role in Redis/DDB
            arn_parsed = parse_arn(extended_request.principal.principal_arn)
            if arn_parsed["service"] == "iam" and arn_parsed["resource"] == "role":
                await IAMRole.get(
                    account_id,
                    extended_request.principal.principal_arn,
                    host,
                    force_refresh=True,
                )
            log_data["request"] = extended_request.dict()
            log_data["message"] = "Applied changes based on approved request"
            log_data["response"] = response.dict()
            log.debug(log_data)

        await aws.send_communications_new_policy_request(
            extended_request, admin_approved, approval_probe_approved, host
        )
        await send_slack_notification_new_request(
            extended_request, admin_approved, approval_probe_approved, host
        )
        self.write(response.json())
        await self.finish()
        return


class RequestsHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests

    Api endpoint to list and filter policy requests.
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/requests
        """
        host = self.ctx.host
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        markdown = arguments.get("markdown")
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        # TODO: Add server-side sorting
        # sort = arguments.get("sort")
        limit = arguments.get("limit", 1000)
        tags = {
            "user": self.user,
            "host": host,
        }
        stats.count("RequestsHandler.post", tags=tags)
        log_data = {
            "function": "RequestsHandler.post",
            "user": self.user,
            "message": "Writing requests",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)
        requests = [
            request.dict() for request in await aio_wrapper(IAMRequest.query, host)
        ]

        total_count = len(requests)

        if filters:
            try:
                with Timeout(seconds=5):
                    for filter_key, filter_value in filters.items():
                        requests = await filter_table(
                            filter_key, filter_value, requests
                        )
            except TimeoutError:
                self.write("Query took too long to run. Check your filter.")
                await self.finish()
                raise

        if markdown:
            requests_to_write = []
            for request in requests[:limit]:
                principal_arn = request.get("principal", {}).get("principal_arn", "")
                url = request.get("principal", {}).get("resource_url", "")
                resource_name = principal_arn
                if "/" in resource_name:
                    resource_name = resource_name.split("/")[-1]
                if not resource_name:
                    resource_name = request.get("principal", {}).get(
                        "resource_identifier"
                    )

                if principal_arn and principal_arn.count(":") == 5 and not url:

                    region = principal_arn.split(":")[3]
                    service_type = principal_arn.split(":")[2]
                    account_id = principal_arn.split(":")[4]
                    if request.get("principal", {}).get("principal_arn"):
                        try:
                            url = await get_url_for_resource(
                                principal_arn,
                                host,
                                service_type,
                                account_id,
                                region,
                                resource_name,
                            )
                        except ResourceNotFound:
                            pass
                # Convert request_id and role ARN to link
                request_url = request.get("extended_request", {}).get("request_url")
                if not request_url:
                    request_url = f"/policies/request/{request['request_id']}"
                request["request_id"] = f"[{request['request_id']}]({request_url})"
                if url:
                    request["arn"] = f"[{principal_arn or resource_name}]({url})"
                requests_to_write.append(request)
        else:
            requests_to_write = requests[0:limit]
        filtered_count = len(requests_to_write)
        res = DataTableResponse(
            totalCount=total_count, filteredCount=filtered_count, data=requests_to_write
        )
        self.write(res.json())
        return


class RequestDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/requests/{request_id}

    Allows read and update access to a specific request.
    """

    allowed_methods = ["GET", "PUT"]

    def on_finish(self) -> None:
        if self.request.method != "PUT":
            return
        from common.celery_tasks.celery_tasks import app as celery_app

        host = self.ctx.host
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            kwargs={"host": host},
        )

    async def _get_extended_request(self, request_id, log_data, host):
        request: IAMRequest = await IAMRequest.get(host, request_id=request_id)
        if not request:
            log_data["message"] = "Request with that ID not found"
            log.warning(log_data)
            stats.count(
                f"{log_data['function']}.not_found",
                tags={
                    "user": self.user,
                    "host": host,
                },
            )
            raise NoMatchingRequest(log_data["message"])

        if request.version != "2":
            # Request format is not compatible with this endpoint version
            raise InvalidRequestParameter("Request with that ID is not a v2 request")

        extended_request = ExtendedRequestModel.parse_obj(
            request.extended_request.dict()
        )
        return extended_request, request.last_updated

    async def get(self, request_id):
        """
        GET /api/v2/requests/{request_id}
        """
        host = self.ctx.host
        tags = {
            "user": self.user,
            "host": host,
        }
        stats.count("RequestDetailHandler.get", tags=tags)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Get request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy_request_id": request_id,
            "host": host,
        }
        log.debug(log_data)
        if (
            config.get_host_specific_key(
                "policy_editor.disallow_contractors", host, True
            )
            and self.contractor
        ):
            if self.user not in config.get_host_specific_key(
                "groups.can_bypass_contractor_restrictions",
                host,
                [],
            ):
                self.write_error(
                    403, message="Only FTEs are authorized to view this page."
                )
                return

        try:
            extended_request, last_updated = await self._get_extended_request(
                request_id, log_data, host
            )
        except InvalidRequestParameter as e:
            sentry_sdk.capture_exception(tags={"user": self.user})
            self.write_error(400, message="Error validating input: " + str(e))
            return
        except NoMatchingRequest as e:
            sentry_sdk.capture_exception(tags={"user": self.user})
            self.write_error(404, message="Error getting request:" + str(e))
            return
        # Run these tasks concurrently.
        concurrent_results = await asyncio.gather(
            populate_old_policies(extended_request, self.user, host),
            populate_cross_account_resource_policies(extended_request, self.user, host),
            populate_old_managed_policies(extended_request, self.user, host),
        )
        extended_request = concurrent_results[0]

        populate_cross_account_resource_policies_result = concurrent_results[1]

        if populate_cross_account_resource_policies_result["changed"]:
            extended_request = populate_cross_account_resource_policies_result[
                "extended_request"
            ]
            # Update in dynamo with the latest resource policy changes
            updated_request = await IAMRequest.write_v2(extended_request, host)
            last_updated = updated_request.last_updated

        populate_old_managed_policies_result = concurrent_results[2]

        if populate_old_managed_policies_result["changed"]:
            extended_request = populate_old_managed_policies_result["extended_request"]
            # Update in dynamo with the latest resource policy changes
            updated_request = await IAMRequest.write_v2(extended_request, host)
            last_updated = updated_request.last_updated

        accounts_ids = await get_extended_request_account_ids(extended_request, host)
        can_approve_reject = await can_admin_policies(
            self.user, self.groups, host, accounts_ids
        )

        can_update_cancel = await can_update_cancel_requests_v2(
            extended_request, self.user, self.groups, host
        )
        can_move_back_to_pending = await can_move_back_to_pending_v2(
            extended_request, last_updated, self.user, self.groups, host
        )

        # In the future request_specific_config will have specific approvers for specific changes based on ABAC
        request_specific_config = {
            "can_approve_reject": can_approve_reject,
            "can_update_cancel": can_update_cancel,
            "can_move_back_to_pending": can_move_back_to_pending,
        }

        template = None
        arn_parsed = parse_arn(extended_request.principal.principal_arn)
        if arn_parsed["service"] == "iam" and arn_parsed["resource"] == "role":
            iam_role = await IAMRole.get(
                arn_parsed["account"], extended_request.principal.principal_arn, host
            )
            template = iam_role.templated

        changes_config = await populate_approve_reject_policy(
            extended_request, self.groups, host, self.user
        )

        response = {
            "request": extended_request.json(),
            "last_updated": last_updated,
            "request_config": request_specific_config,
            "changes_config": changes_config,
            "template": template,
        }

        self.write(response)

    async def put(self, request_id):
        """
        PUT /api/v2/requests/{request_id}
        """
        host = self.ctx.host
        tags = {
            "user": self.user,
            "host": host,
        }
        stats.count("RequestDetailHandler.put", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.put",
            "user": self.user,
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy_request_id": request_id,
            "host": host,
        }
        log.debug(log_data)

        if (
            config.get_host_specific_key(
                "policy_editor.disallow_contractors", host, True
            )
            and self.contractor
        ):
            if self.user not in config.get_host_specific_key(
                "groups.can_bypass_contractor_restrictions",
                host,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        try:
            # Validate the request body
            request_changes = PolicyRequestModificationRequestModel.parse_raw(
                self.request.body
            )
            log_data["message"] = "Parsed request body"
            log_data["request"] = request_changes.dict()
            log.debug(log_data)

            extended_request, last_updated = await self._get_extended_request(
                request_id, log_data, host
            )

            if any(
                change.change_type == "tear_can_assume_role"
                for change in extended_request.changes.changes
            ):
                change_info = request_changes.modification_model
                if (
                    hasattr(change_info, "expiration_date")
                    and not change_info.expiration_date
                ):
                    raise ValueError(
                        "An expiration date must be provided for elevated access requests."
                    )

            response = await parse_and_apply_policy_request_modification(
                extended_request,
                request_changes,
                self.user,
                self.groups,
                last_updated,
                host,
            )

        except (
            NoMatchingRequest,
            InvalidRequestParameter,
            ValidationError,
            ValueError,
        ) as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception(tags={"user": self.user})
            stats.count(
                f"{log_data['function']}.validation_exception",
                tags={
                    "user": self.user,
                    "host": host,
                },
            )
            self.write_error(400, message="Error validating input: " + str(e))
            if config.get("_global_.development"):
                raise
            return
        except Unauthorized as e:
            log_data["message"] = "Unauthorized"
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception(tags={"user": self.user})
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "user": self.user,
                    "host": host,
                },
            )
            self.write_error(403, message=str(e))
            if config.get("_global_.development"):
                raise
            return
        self.write(response.json())
        await self.finish()
        return


class RequestsPageConfigHandler(BaseHandler):
    async def get(self):
        """
        /requests_page_config
        ---
        get:
            description: Retrieve Requests Page Configuration
            responses:
                200:
                    description: Returns Requests Page Configuration
        """
        host = self.ctx.host
        default_configuration = {
            "pageName": "Requests",
            "pageDescription": "View all IAM policy requests created through ConsoleMe",
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v2/requests?markdown=true",
                "sortable": False,
                "totalRows": 200,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "allowCsvExport": True,
                "allowJsonExport": True,
                "columns": [
                    {
                        "placeholder": "Username",
                        "key": "username",
                        "type": "input",
                        "style": {"width": "100px"},
                    },
                    {
                        "placeholder": "Arn",
                        "key": "arn",
                        "type": "link",
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                        "width": 3,
                    },
                    {
                        "placeholder": "Request Time",
                        "key": "request_time",
                        "type": "daterange",
                    },
                    {
                        "placeholder": "Status",
                        "key": "status",
                        "type": "dropdown",
                        "style": {"width": "90px"},
                    },
                    {
                        "placeholder": "Request ID",
                        "key": "request_id",
                        "type": "link",
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                        "width": 2,
                    },
                ],
            },
        }

        table_configuration = config.get_host_specific_key(
            "RequestsTableConfigHandler.configuration",
            host,
            default_configuration,
        )

        self.write(table_configuration)
