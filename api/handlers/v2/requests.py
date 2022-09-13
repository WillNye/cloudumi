import asyncio
import sys
import time
import uuid
from datetime import datetime

import sentry_sdk
from policy_sentry.util.arns import parse_arn
from pydantic import ValidationError

import common.lib.noq_json as json
from common.aws.iam.role.models import IAMRole
from common.aws.utils import ResourceAccountCache, ResourceSummary, get_url_for_resource
from common.config import config
from common.exceptions.exceptions import (
    InvalidRequestParameter,
    MustBeFte,
    NoMatchingRequest,
    ResourceNotFound,
    Unauthorized,
)
from common.handlers.base import BaseAPIV2Handler, BaseHandler
from common.lib.auth import (
    can_admin_policies,
    get_extended_request_account_ids,
    populate_approve_reject_policy,
)
from common.lib.aws.cached_resources.iam import get_tra_supported_roles_by_tag
from common.lib.generic import filter_table, write_json_error
from common.lib.mfa import mfa_verify
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import (
    can_move_back_to_pending_v2,
    can_update_cancel_requests_v2,
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
    update_changes_meta_data,
)
from common.models import (
    Command,
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
from common.user_request.utils import (
    TRA_CONFIG_BASE_KEY,
    get_tra_config,
    normalize_expiration_date,
)

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


async def validate_request_creation(
    handler, request: RequestCreationModel
) -> RequestCreationModel:
    err = ""
    request = normalize_expiration_date(request)

    if tra_change := next(
        (c for c in request.changes.changes if c.change_type == "tra_can_assume_role"),
        None,
    ):
        tenant = handler.ctx.tenant
        role_arn = tra_change.principal.principal_arn
        tra_supported_roles = await get_tra_supported_roles_by_tag(
            handler.eligible_roles, handler.groups, tenant
        )
        tra_supported_role = [
            role["arn"] for role in tra_supported_roles if role["arn"] == role_arn
        ]

        if not tra_supported_role:
            err += f"No TRA support for {tra_change.principal.principal_arn} or access already exists. "

        if not request.expiration_date and not request.ttl:
            err += "expiration_date or ttl is a required field for temporary role access requests. "

        if err:
            handler.set_status(400)
            handler.write(
                WebResponse(staus=WebStatus.error, errors=[err]).json(
                    exclude_unset=True, exclude_none=True
                )
            )
            return await handler.finish()

        resource_summary = await ResourceSummary.set(tenant, role_arn)
        tra_config = await get_tra_config(resource_summary)
        if tra_config.mfa.enabled:
            is_authenticated, err = await mfa_verify(handler.ctx.tenant, handler.user)
            if not is_authenticated:
                handler.set_status(403)
                handler.write(
                    WebResponse(staus=WebStatus.error, errors=[err]).json(
                        exclude_unset=True, exclude_none=True
                    )
                )
                return await handler.finish()

        request.admin_auto_approve = False

    if err:
        handler.set_status(400)
        handler.write(
            WebResponse(staus=WebStatus.error, errors=[err]).json(
                exclude_unset=True, exclude_none=True
            )
        )
        return await handler.finish()

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

        tenant = self.ctx.tenant
        try:
            with Timeout(
                seconds=5, error_message="Timeout: Are you sure Celery is running?"
            ):
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
                    kwargs={"tenant": tenant},
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
                        "Sid": "AllowNoqProdAssumeRoles"
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
        tenant = self.ctx.tenant
        if (
            config.get_tenant_specific_key(
                "policy_editor.disallow_contractors", tenant, True
            )
            and self.contractor
        ):
            if self.user not in config.get_tenant_specific_key(
                "groups.can_bypass_contractor_restrictions",
                tenant,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        tags = {
            "user": self.user,
            "tenant": tenant,
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
            "rule_auto_approved": False,
            "tenant": tenant,
        }
        aws = get_plugin_by_name(
            config.get_tenant_specific_key("plugins.aws", tenant, "cmsaas_aws")
        )()
        log.debug(log_data)
        try:
            # Validate the model
            changes = RequestCreationModel.parse_raw(self.request.body)
            if not changes.dry_run:
                changes = await validate_request_creation(self, changes)

            extended_request = await generate_request_from_change_model_array(
                changes, self.user, tenant
            )
        except Exception as err:
            extended_request = None
            log_data["error"] = str(err)
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception(tags={"user": self.user})

        if not extended_request:
            response = RequestCreationResponse(
                errors=1, request_created=False, action_results=[]
            )
            self.write(response.json())
            await self.finish()
            return

        try:
            log_data["request"] = extended_request.dict()
            log.debug(log_data)

            await update_changes_meta_data(extended_request, tenant)

            if changes.dry_run:
                response = RequestCreationResponse(
                    errors=0, request_created=False, extended_request=extended_request
                )
                self.write(response.json())
                await self.finish()
                return

            admin_approved = False
            approval_rule_approved = False
            auto_approved = False

            if extended_request.principal.principal_type == "AwsResource":
                # TODO: Provide a note to the requester that admin_auto_approve will apply the requested policies only.
                # It will not automatically apply generated policies. The administrative user will need to visit
                # the policy request page to do this manually.
                if changes.admin_auto_approve:
                    # make sure user is allowed to use admin_auto_approve
                    account_ids = await get_extended_request_account_ids(
                        extended_request, tenant
                    )
                    can_manage_policy_request = (
                        await can_admin_policies(
                            self.user, self.groups, tenant, account_ids
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
                                "tenant": tenant,
                            },
                        )
                    else:
                        # someone is trying to use admin bypass without being an admin, don't allow request to proceed
                        stats.count(
                            f"{log_data['function']}.post.unauthorized_admin_bypass",
                            tags={
                                "user": self.user,
                                "tenant": tenant,
                            },
                        )
                        log_data[
                            "message"
                        ] = "Unauthorized user trying to use admin bypass"
                        log.error(log_data)
                        await write_json_error("Unauthorized", obj=self)
                        return
                else:
                    # If admin auto approve is false, check for auto-approve rule eligibility
                    is_eligible_for_auto_approve = (
                        await is_request_eligible_for_auto_approval(
                            tenant, extended_request, self.user, self.groups
                        )
                    )
                    is_tra_request = bool(
                        len(extended_request.changes.changes) == 1
                        and extended_request.changes.changes[0].change_type
                        == "tra_can_assume_role"
                    )
                    if is_eligible_for_auto_approve and is_tra_request:
                        extended_request.request_status = RequestStatus.approved
                        stats.count(
                            f"{log_data['function']}.tra_auto_approved",
                            tags={
                                "user": self.user,
                                "tenant": tenant,
                            },
                        )
                        tra_approval_comment = CommentModel(
                            id=str(uuid.uuid4()),
                            timestamp=int(time.time()),
                            user_email="NOQ",
                            last_modified=int(time.time()),
                            text="Temporary role access auto-approved based on config",
                        )
                        extended_request.comments.append(tra_approval_comment)
                        extended_request.reviewer = f"Auto-Approved as determined by your {TRA_CONFIG_BASE_KEY} config"
                        log_data["tra_auto_approved"] = True
                        log_data["request"] = extended_request.dict()
                        log.debug(log_data)
                        auto_approved = True

                    elif is_eligible_for_auto_approve:
                        # If we have only made requests that are eligible for auto-approval rule, check against them
                        should_auto_approve_request = (
                            await should_auto_approve_policy_v2(
                                extended_request, self.user, self.groups, tenant
                            )
                        )
                        if should_auto_approve_request["approved"]:
                            extended_request.request_status = RequestStatus.approved
                            approval_rule_approved = True
                            stats.count(
                                f"{log_data['function']}.rule_auto_approved",
                                tags={
                                    "user": self.user,
                                    "tenant": tenant,
                                },
                            )
                            approving_rules = []
                            for approving_rule in should_auto_approve_request.get(
                                "approving_rules", []
                            ):
                                approving_rule_comment = CommentModel(
                                    id=str(uuid.uuid4()),
                                    timestamp=int(time.time()),
                                    user_email=f"Auto-Approve Rule: {approving_rule['name']}",
                                    last_modified=int(time.time()),
                                    text=(
                                        f"Policy {approving_rule['policy']} auto-approved by rule: "
                                        f"{approving_rule['name']}"
                                    ),
                                )
                                extended_request.comments.append(approving_rule_comment)
                                approving_rules.append(approving_rule["name"])
                            extended_request.reviewer = (
                                f"Auto-Approve Rule: {','.join(approving_rules)}"
                            )
                            log_data["rule_auto_approved"] = True
                            log_data["request"] = extended_request.dict()
                            log.debug(log_data)

            request = await IAMRequest.write_v2(extended_request, tenant)
            log_data["message"] = "New request created in Dynamo"
            log_data["request"] = extended_request.dict()
            log_data["dynamo_request"] = request.dict()
            log.debug(log_data)
        except (InvalidRequestParameter, ValidationError):
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            request_url = await get_request_url(extended_request)
            res = RequestCreationResponse(
                errors=1,
                request_created=True,
                request_id=extended_request.id,
                request_url=request_url,
                action_results=[],
                extended_request=extended_request,
            )

            self.write(res.json(exclude_unset=True, exclude_none=True))
            if config.get("_global_.development"):
                raise
            return
        except Exception:
            log_data["message"] = "Unknown Exception occurred while parsing request"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception(tags={"user": self.user})
            request_url = await get_request_url(extended_request)
            res = RequestCreationResponse(
                errors=1,
                request_created=True,
                request_id=extended_request.id,
                request_url=request_url,
                action_results=[],
                extended_request=extended_request,
            )

            self.write(res.json(exclude_unset=True, exclude_none=True))
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

        # If approved is true due to an auto-approval rule or admin auto-approval, apply the non-autogenerated changes
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

                log.warning(
                    {
                        "message": f"Calling parse_and_apply_policy_request_modification with {auto_approved}"
                    }
                )

                policy_apply_response = (
                    await parse_and_apply_policy_request_modification(
                        extended_request,
                        policy_request_modification_model,
                        self.user,
                        self.groups,
                        int(time.time()),
                        tenant,
                        approval_rule_approved=approval_rule_approved,
                        cloud_credentials=changes.credentials,
                        auto_approved=auto_approved,
                    )
                )
                response.errors = policy_apply_response.errors
                response.action_results = policy_apply_response.action_results

            # Update in dynamo
            await IAMRequest.write_v2(extended_request, tenant)
            account_id = await ResourceAccountCache.get(
                tenant, extended_request.principal.principal_arn
            )

            # Force a refresh of the role in Redis/DDB
            arn_parsed = parse_arn(extended_request.principal.principal_arn)
            if arn_parsed["service"] == "iam" and arn_parsed["resource"] == "role":
                await IAMRole.get(
                    tenant,
                    account_id,
                    extended_request.principal.principal_arn,
                    force_refresh=True,
                )
            log_data["request"] = extended_request.dict()
            log_data["message"] = "Applied changes based on approved request"
            log_data["response"] = response.dict()
            log.debug(log_data)

        if not auto_approved:
            await aws.send_communications_new_policy_request(
                extended_request, admin_approved, approval_rule_approved, tenant
            )

        await send_slack_notification_new_request(
            extended_request, admin_approved, approval_rule_approved, tenant
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
        tenant = self.ctx.tenant
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        markdown = arguments.get("markdown")
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        # TODO: Add server-side sorting
        # sort = arguments.get("sort")
        limit = arguments.get("limit", 1000)
        tags = {
            "user": self.user,
            "tenant": tenant,
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
            "tenant": tenant,
        }
        log.debug(log_data)
        requests = [request.dict() for request in await IAMRequest.query(tenant)]

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
                    resource_summary = await ResourceSummary.set(
                        tenant, principal_arn, account_required=False
                    )
                    if resource_summary.account and request.get("principal", {}).get(
                        "principal_arn"
                    ):
                        try:
                            url = await get_url_for_resource(resource_summary)
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

        requests_to_write = sorted(
            requests_to_write, key=lambda d: d["request_time"], reverse=True
        )
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

        tenant = self.ctx.tenant
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            kwargs={"tenant": tenant},
        )

    async def _get_extended_request(self, request_id, log_data, tenant):
        request: IAMRequest = await IAMRequest.get(tenant, request_id=request_id)
        if not request:
            log_data["message"] = "Request with that ID not found"
            log.warning(log_data)
            stats.count(
                f"{log_data['function']}.not_found",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            raise NoMatchingRequest(log_data["message"])

        if request.version != "2":
            # Request format is not compatible with this endpoint version
            raise InvalidRequestParameter("Request with that ID is not a v2 request")

        await request.set_change_metadata()
        extended_request = ExtendedRequestModel.parse_obj(
            await request.get_extended_request_dict()
        )
        return extended_request, request.last_updated

    async def get(self, request_id):
        """
        GET /api/v2/requests/{request_id}
        """
        tenant = self.ctx.tenant
        tags = {
            "user": self.user,
            "tenant": tenant,
        }
        stats.count("RequestDetailHandler.get", tags=tags)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Get request details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy_request_id": request_id,
            "tenant": tenant,
        }
        log.debug(log_data)
        if (
            config.get_tenant_specific_key(
                "policy_editor.disallow_contractors", tenant, True
            )
            and self.contractor
        ):
            if self.user not in config.get_tenant_specific_key(
                "groups.can_bypass_contractor_restrictions",
                tenant,
                [],
            ):
                self.write_error(
                    403, message="Only FTEs are authorized to view this page."
                )
                return

        try:
            extended_request, last_updated = await self._get_extended_request(
                request_id, log_data, tenant
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
            populate_old_policies(extended_request, self.user, tenant),
            populate_cross_account_resource_policies(
                extended_request, self.user, tenant
            ),
            populate_old_managed_policies(extended_request, self.user, tenant),
        )
        extended_request = concurrent_results[0]

        populate_cross_account_resource_policies_result = concurrent_results[1]

        if populate_cross_account_resource_policies_result["changed"]:
            extended_request = populate_cross_account_resource_policies_result[
                "extended_request"
            ]
            # Update in dynamo with the latest resource policy changes
            updated_request = await IAMRequest.write_v2(extended_request, tenant)
            last_updated = updated_request.last_updated

            # Refresh the commands now that the policies in the script have changed
            await updated_request.set_change_metadata()
            extended_request = ExtendedRequestModel.parse_obj(
                await updated_request.get_extended_request_dict()
            )

        populate_old_managed_policies_result = concurrent_results[2]
        if populate_old_managed_policies_result["changed"]:
            extended_request = populate_old_managed_policies_result["extended_request"]
            # Update in dynamo with the latest resource policy changes
            updated_request = await IAMRequest.write_v2(extended_request, tenant)
            last_updated = updated_request.last_updated

            # Refresh the commands now that the policies in the script have changed
            await updated_request.set_change_metadata()
            extended_request = ExtendedRequestModel.parse_obj(
                await updated_request.get_extended_request_dict()
            )

        accounts_ids = await get_extended_request_account_ids(extended_request, tenant)
        can_approve_reject = await can_admin_policies(
            self.user, self.groups, tenant, accounts_ids
        )

        can_update_cancel = await can_update_cancel_requests_v2(
            extended_request, self.user, self.groups, tenant
        )
        can_move_back_to_pending = await can_move_back_to_pending_v2(
            extended_request, last_updated, self.user, self.groups, tenant
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
                tenant, arn_parsed["account"], extended_request.principal.principal_arn
            )
            template = iam_role.templated

        changes_config = await populate_approve_reject_policy(
            extended_request, self.groups, tenant, self.user
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
        tenant = self.ctx.tenant
        tags = {
            "user": self.user,
            "tenant": tenant,
        }
        stats.count("RequestDetailHandler.put", tags=tags)
        log_data = {
            "function": "RequestDetailHandler.put",
            "user": self.user,
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy_request_id": request_id,
            "tenant": tenant,
        }
        log.debug(log_data)

        if (
            config.get_tenant_specific_key(
                "policy_editor.disallow_contractors", tenant, True
            )
            and self.contractor
        ):
            if self.user not in config.get_tenant_specific_key(
                "groups.can_bypass_contractor_restrictions",
                tenant,
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
                request_id, log_data, tenant
            )
            change_info = request_changes.modification_model
            is_expiry_update = bool(
                change_info.command
                in [Command.update_expiration_date, Command.update_ttl]
            )
            has_expiry_info = bool(
                getattr(
                    change_info, "expiration_date", getattr(change_info, "ttl", None)
                )
            )

            if is_expiry_update and any(
                change.change_type == "tra_can_assume_role"
                for change in extended_request.changes.changes
            ):
                if not has_expiry_info:
                    raise ValueError(
                        "A valid expiration date or ttl must be provided for temporary role access requests."
                    )
            if (
                is_expiry_update
                and extended_request.request_status != RequestStatus.pending
            ):
                raise ValueError(
                    "The TTL and expiration date can only be updated on pending requests."
                )
            if (
                any(
                    change.change_type == "policy_condenser"
                    for change in extended_request.changes.changes
                )
                and has_expiry_info
            ):
                raise ValueError(
                    "Expiration dates and TTLs are not supported for policy condenser requests."
                )

            response = await parse_and_apply_policy_request_modification(
                extended_request,
                request_changes,
                self.user,
                self.groups,
                last_updated,
                tenant,
                cloud_credentials=getattr(
                    request_changes.modification_model, "credentials", None
                ),
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
                    "tenant": tenant,
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
                    "tenant": tenant,
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
        tenant = self.ctx.tenant
        default_configuration = {
            "pageName": "Requests",
            "pageDescription": "View all IAM policy requests created through Noq",
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
                        "placeholder": "Request ID",
                        "key": "request_id",
                        "type": "link",
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                        "width": 4,
                    },
                    {
                        "placeholder": "Username",
                        "key": "username",
                        "type": "input",
                        "width": 3,
                    },
                    {
                        "placeholder": "Arn",
                        "key": "arn",
                        "type": "link",
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                        "width": 5,
                    },
                    {
                        "placeholder": "Request Time",
                        "key": "request_time",
                        "type": "daterange",
                        "width": 2,
                    },
                    {
                        "placeholder": "Status",
                        "key": "status",
                        "type": "dropdown",
                        "width": 1,
                    },
                ],
            },
        }

        table_configuration = config.get_tenant_specific_key(
            "RequestsTableConfigHandler.configuration",
            tenant,
            default_configuration,
        )

        self.write(table_configuration)
