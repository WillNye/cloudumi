import asyncio
import re
import sys
import time
import uuid
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Dict, List, Optional, Union

import sentry_sdk
from botocore.exceptions import ClientError
from dateutil import parser
from policy_sentry.util.actions import get_service_from_action
from policy_sentry.util.arns import parse_arn

import common.lib.noq_json as json
from common.aws.iam.policy.utils import (
    aio_get_managed_policy_document,
    aio_list_managed_policies_for_resource,
    create_or_update_managed_policy,
    generate_updated_resource_policy,
    get_managed_policy_document,
    get_resource_policy,
)
from common.aws.iam.role.models import IAMRole
from common.aws.iam.utils import get_supported_resource_permissions, get_tenant_iam_conn
from common.aws.utils import (
    ResourceAccountCache,
    ResourceSummary,
    get_resource_tag,
    get_url_for_resource,
)
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import (
    InvalidRequestParameter,
    NoMatchingRequest,
    ResourceNotFound,
    Unauthorized,
    UnsupportedChangeType,
)
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import NoqSemaphore, aio_wrapper
from common.lib.auth import can_admin_policies, get_extended_request_account_ids
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.utils import delete_iam_user, fetch_resource_details
from common.lib.change_request import generate_policy_name, generate_policy_sid
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import (
    can_move_back_to_pending_v2,
    can_update_cancel_requests_v2,
    invalid_characters_in_policy,
    send_communications_new_comment,
    send_communications_policy_change_request_v2,
)
from common.lib.templated_resources.requests import (
    generate_honeybee_request_from_change_model_array,
)
from common.lib.terraform.requests import (
    generate_terraform_request_from_change_model_array,
)
from common.lib.v2.aws_principals import get_role_details, get_user_details
from common.models import (
    Action,
    Action1,
    ActionResult,
    ApplyChangeModificationModel,
    AssumeRolePolicyChangeModel,
    AWSCredentials,
    CancelChangeModificationModel,
    ChangeModel,
    ChangeModelArray,
    CloudCredentials,
    Command,
    CommentModel,
    CommentRequestModificationModel,
    CreateResourceChangeModel,
    DeleteResourceChangeModel,
    ExpirationDateRequestModificationModel,
    ExtendedAwsPrincipalModel,
    ExtendedRequestModel,
    GenericFileChangeModel,
    InlinePolicyChangeModel,
    ManagedPolicyChangeModel,
    ManagedPolicyResourceChangeModel,
    PermissionsBoundaryChangeModel,
    PolicyCondenserChangeModel,
    PolicyModel,
    PolicyRequestModificationRequestModel,
    PolicyRequestModificationResponseModel,
    RequestCreationModel,
    RequestCreationResponse,
    RequestStatus,
    ResourceModel,
    ResourcePolicyChangeModel,
    ResourceTagChangeModel,
    ResourceType,
    RoleAccessChangeModel,
    SpokeAccount,
    Status,
    TagAction,
    TraRoleChangeModel,
    TTLRequestModificationModel,
    UpdateChangeModificationModel,
    UserModel,
)
from common.user_request.models import IAMRequest
from common.user_request.utils import (
    get_active_tra_users_tag,
    get_change_arn,
    get_tra_config_for_request,
    update_extended_request_expiration_date,
    validate_custom_credentials,
)

log = config.get_logger()


async def update_changes_meta_data(extended_request: ExtendedRequestModel, tenant: str):
    for change in extended_request.changes.changes:
        try:
            arn = get_change_arn(change)
            resource_summary = await ResourceSummary.set(tenant, arn)
            account_info: SpokeAccount = (
                ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", tenant)
                .with_query({"account_id": resource_summary.account})
                .first
            )
            change.read_only = account_info.read_only
        except (ValueError, AttributeError):
            # spoke account not available
            pass


async def generate_request_from_change_model_array(
    request_creation: RequestCreationModel,
    user: str,
    tenant: str,
) -> ExtendedRequestModel:
    """
    Compiles an ChangeModelArray and returns a filled out ExtendedRequestModel based on the changes

    :param request_creation: ChangeModelArray
    :param user: Str - requester's email address
    :return: ChangeModelArray
    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "request": request_creation.dict(),
        "message": "Incoming request",
        "tenant": tenant,
    }
    log.info(log_data)
    auth = get_plugin_by_name(
        config.get_tenant_specific_key("plugins.auth", tenant, "cmsaas_auth")
    )()
    primary_principal = None
    change_models = request_creation.changes
    if len(change_models.changes) < 1:
        log_data["message"] = "At least 1 change is required to create a request."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    inline_policy_changes = []
    policy_condenser_changes = []
    managed_policy_changes = []
    resource_policy_changes = []
    assume_role_policy_changes = []
    resource_tag_changes = []
    permissions_boundary_changes = []
    managed_policy_resource_changes = []
    generic_file_changes = []
    tra_role_changes = []
    role_access_changes = []
    create_resource_changes = []
    delete_resource_changes = []
    role = None

    extended_request_uuid = str(uuid.uuid4())
    incremental_change_id = 0
    supported_resource_policies = config.get_tenant_specific_key(
        "policies.supported_resource_types_for_policy_application",
        tenant,
        ["s3", "sqs", "sns"],
    )

    for change in change_models.changes:
        # All changes status must be not-applied at request creation
        change.status = Status.not_applied
        # Add ID for each change
        change.id = extended_request_uuid + str(incremental_change_id)
        incremental_change_id += 1

        # Enforce a maximum of one principal ARN per ChangeGeneratorModelArray (aka Policy Request)
        if not primary_principal:
            primary_principal = change.principal
        if primary_principal != change.principal:
            log_data[
                "message"
            ] = "We only support making changes to a single principal ARN per request."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])

        if change.change_type == "inline_policy":
            inline_policy_changes.append(
                InlinePolicyChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "policy_condenser":
            policy_condenser_changes.append(
                PolicyCondenserChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "managed_policy":
            managed_policy_changes.append(
                ManagedPolicyChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "managed_policy_resource":
            managed_policy_resource_changes.append(
                ManagedPolicyResourceChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "resource_policy":
            change.autogenerated = False
            change.source_change_id = None
            change.supported = (
                parse_arn(change.arn)["service"] in supported_resource_policies
            )
            resource_policy_changes.append(change)
        elif change.change_type == "assume_role_policy":
            assume_role_policy_changes.append(
                AssumeRolePolicyChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "resource_tag":
            resource_tag_changes.append(
                ResourceTagChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "permissions_boundary":
            permissions_boundary_changes.append(
                PermissionsBoundaryChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "generic_file":
            generic_file_changes.append(
                GenericFileChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "tra_can_assume_role":
            tra_role_changes.append(TraRoleChangeModel.parse_obj(change.__dict__))
        elif change.change_type == "assume_role_access":
            role_access_changes.append(RoleAccessChangeModel.parse_obj(change.__dict__))
        elif change.change_type == "create_resource":
            create_resource_changes.append(
                CreateResourceChangeModel.parse_obj(change.__dict__)
            )
        elif change.change_type == "delete_resource":
            delete_resource_changes.append(
                DeleteResourceChangeModel.parse_obj(change.__dict__)
            )
        else:
            raise UnsupportedChangeType(
                f"Invalid `change_type` for change: {change.__dict__}"
            )

    # Make sure the requester is only ever 64 chars with domain
    if len(user) > 64:
        split_items: list = user.split("@")
        user: str = (
            split_items[0][: (64 - (len(split_items[-1]) + 1))] + "@" + split_items[-1]
        )

    if (
        len(change_models.changes) == 1
        and change_models.changes[0].change_type == "create_resource"
    ):
        request_changes = ChangeModelArray(changes=create_resource_changes)
        arn_url = ""
    elif (
        len(change_models.changes) == 1
        and change_models.changes[0].change_type == "delete_resource"
    ):
        request_changes = ChangeModelArray(changes=delete_resource_changes)
        arn_url = change_models.changes[0].principal.principal_arn
    elif primary_principal.principal_type == "AwsResource":
        # TODO: Separate this out into another function
        resource_summary = await ResourceSummary.set(
            tenant, primary_principal.principal_arn
        )
        account_id = resource_summary.account
        try:
            arn_url = await get_url_for_resource(resource_summary)
        except ResourceNotFound:
            # should never reach this case...
            arn_url = ""

        # Only one assume role policy change allowed per request
        if len(assume_role_policy_changes) > 1:
            log_data[
                "message"
            ] = "One one assume role policy change supported per request."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])

        if len(managed_policy_resource_changes) > 0:
            # for managed policy changes, principal arn must be a managed policy
            if (
                resource_summary.service != "iam"
                or resource_summary.resource_type != "policy"
            ):
                log_data[
                    "message"
                ] = "Principal ARN type not supported for managed policy resource changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            if resource_summary.account == "aws":
                log_data["message"] = "AWS Managed Policies aren't valid for changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            if (
                len(inline_policy_changes) > 0
                or len(policy_condenser_changes) > 0
                or len(managed_policy_changes) > 0
                or len(assume_role_policy_changes) > 0
                or len(permissions_boundary_changes) > 0
            ):
                log_data[
                    "message"
                ] = "Principal ARN type not supported for inline/managed/assume role policy changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            if len(managed_policy_resource_changes) > 1:
                log_data[
                    "message"
                ] = "One one managed policy resource change supported per request."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])

            policy_name = resource_summary.name
            managed_policy_resource = None
            try:
                managed_policy_resource = await aio_wrapper(
                    get_managed_policy_document,
                    tenant=tenant,
                    policy_arn=primary_principal.principal_arn,
                    account_number=account_id,
                    assume_role=ModelAdapter(SpokeAccount)
                    .load_config("spoke_accounts", tenant)
                    .with_query({"account_id": account_id})
                    .first.name,
                    region=config.region,
                    retry_max_attempts=2,
                )
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchEntity":
                    # Could be a new managed policy, hence not found
                    pass
                else:
                    log_data[
                        "message"
                    ] = "Exception raised while getting managed policy"
                    log.error(log_data, exc_info=True)
                    raise InvalidRequestParameter(log_data["message"] + ": " + str(e))

            for managed_policy_resource_change in managed_policy_resource_changes:
                await validate_managed_policy_resource_change(
                    managed_policy_resource_change,
                    policy_name,
                    user,
                    managed_policy_resource,
                )

        elif (
            len(inline_policy_changes) > 0
            or len(policy_condenser_changes) > 0
            or len(managed_policy_changes) > 0
            or len(assume_role_policy_changes) > 0
            or len(permissions_boundary_changes) > 0
            or len(tra_role_changes) > 0
            or len(role_access_changes) > 0
        ):
            # for inline/managed/assume role policies, principal arn must be a role
            if (
                resource_summary.service != "iam"
                or resource_summary.resource_type
                not in [
                    "role",
                    "user",
                ]
            ):
                log_data[
                    "message"
                ] = "Resource not found, or ARN type not supported for inline/managed/assume role policy changes."
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])
            principal_name = resource_summary.name
            principal_details = None
            if resource_summary.resource_type == "role":
                principal_details = await get_role_details(
                    account_id, principal_name, tenant, extended=True
                )
            elif resource_summary.resource_type == "user":
                principal_details = await get_user_details(
                    account_id, principal_name, tenant, extended=True
                )
            if not principal_details:
                log_data["message"] = "Principal not found"
                log.error(log_data)
                raise InvalidRequestParameter(log_data["message"])
            for inline_policy_change in inline_policy_changes:
                inline_policy_change.policy_name = await generate_policy_name(
                    inline_policy_change.policy_name,
                    user,
                    tenant,
                    request_creation.expiration_date,
                )
                await validate_inline_policy_change(
                    inline_policy_change, user, principal_details
                )
            for policy_condenser_change in policy_condenser_changes:
                policy_condenser_change.policy_name = await generate_policy_name(
                    policy_condenser_change.policy_name,
                    user,
                    tenant,
                    request_creation.expiration_date,
                )
                await validate_inline_policy_change(
                    policy_condenser_change, user, principal_details
                )
            for managed_policy_change in managed_policy_changes:
                await validate_managed_policy_change(
                    managed_policy_change, user, principal_details
                )
            for permissions_boundary_change in permissions_boundary_changes:
                await validate_permissions_boundary_change(
                    permissions_boundary_change, user, principal_details
                )
            for assume_role_policy_change in assume_role_policy_changes:
                if resource_summary.resource_type == "user":
                    raise UnsupportedChangeType(
                        "Unable to modify an assume role policy associated with an IAM user"
                    )
                await validate_assume_role_policy_change(
                    assume_role_policy_change, user, principal_details
                )
            for resource_tag_change in resource_tag_changes:
                await validate_resource_tag_change(
                    resource_tag_change, user, principal_details
                )

        # TODO: validate resource policy logic when we are ready to apply that

        # If here, request is valid and can successfully be generated
        request_changes = ChangeModelArray(
            changes=inline_policy_changes
            + policy_condenser_changes
            + managed_policy_changes
            + resource_policy_changes
            + assume_role_policy_changes
            + resource_tag_changes
            + permissions_boundary_changes
            + managed_policy_resource_changes
            + tra_role_changes
            + role_access_changes
        )
    elif primary_principal.principal_type == "HoneybeeAwsResourceTemplate":
        # TODO: Generate extended request from HB template
        return await generate_honeybee_request_from_change_model_array(
            request_creation, user, extended_request_uuid, tenant
        )
    elif primary_principal.principal_type == "TerraformAwsResource":
        # TODO: Support Terraform!!
        return await generate_terraform_request_from_change_model_array(
            request_creation, user, extended_request_uuid, tenant
        )
    else:
        raise Exception("Unknown principal type")

    extended_request = ExtendedRequestModel(
        admin_auto_approve=request_creation.admin_auto_approve,
        expiration_date=request_creation.expiration_date,
        ttl=request_creation.ttl,
        id=extended_request_uuid,
        principal=primary_principal,
        timestamp=int(time.time()),
        justification=request_creation.justification,
        requester_email=user,
        approvers=[],  # TODO: approvers logic (future feature)
        request_status=RequestStatus.pending,
        changes=request_changes,
        requester_info=UserModel(
            email=user,
            extended_info=await auth.get_user_info(user, tenant),
            details_url=config.get_employee_info_url(user, tenant),
            photo_url=config.get_employee_photo_url(user, tenant),
        ),
        comments=[],
        cross_account=False,
        arn_url=arn_url,
    )

    if primary_principal.principal_arn:
        extended_request = await populate_old_policies(
            extended_request, user, tenant, role
        )
        extended_request = await generate_resource_policies(
            extended_request, user, tenant
        )
        if len(managed_policy_resource_changes) > 0:
            await populate_old_managed_policies(extended_request, user, tenant)
    return extended_request


async def get_request_url(extended_request: ExtendedRequestModel) -> str:
    if extended_request.principal.principal_type == "AwsResource":
        return f"/policies/request/{extended_request.id}"
    elif extended_request.principal.principal_type in [
        "HoneybeeAwsResourceTemplate",
        "TerraformAwsResource",
    ]:
        return extended_request.request_url
    else:
        raise Exception("Unsupported principal type")


async def is_request_eligible_for_auto_approval(
    tenant: str,
    extended_request: ExtendedRequestModel,
    user: str,
    user_groups: list[str],
) -> bool:
    """
    Checks whether a request is eligible for auto-approval rules or not. Currently, only requests with inline_policies
    are eligible for auto-approval rules.

    :param tenant:
    :param extended_request: ExtendedRequestModel
    :param user: username
    :param user_groups: The groups the user belongs to
    :return bool:
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": extended_request.principal.principal_arn,
        "request": extended_request.dict(),
        "message": "Checking whether request is eligible for auto-approval rules",
    }
    log.info(log_data)
    is_eligible = False

    # We won't auto-approve any requests for Read-Only accounts
    if any(change.read_only is True for change in extended_request.changes.changes):
        return is_eligible

    potentially_eligible_change_types = [
        "resource_policy",
        "sts_resource_policy",
        "inline_policy",
        "tra_can_assume_role",
    ]

    if any(
        change.change_type not in potentially_eligible_change_types
        for change in extended_request.changes.changes
    ):
        return is_eligible

    # The only change types which can be eligible are: Inline policies and TRA (if requires_approval == False)
    for change in extended_request.changes.changes:
        if change.change_type == "tra_can_assume_role":
            tra_config = await get_tra_config_for_request(
                tenant, extended_request.principal.principal_arn, user_groups
            )
            # Does not require approval so can auto approve
            is_eligible = not tra_config.requires_approval
            if not is_eligible:
                return is_eligible
        elif change.change_type == "inline_policy":
            is_eligible = True

    log_data[
        "message"
    ] = "Finished checking whether request is eligible for auto-approval rules"
    log_data["eligible_for_auto_approval"] = is_eligible
    log.info(log_data)
    return is_eligible


async def update_resource_in_dynamo(tenant: str, arn: str, force_refresh: bool):
    resource_summary = await ResourceSummary.set(tenant, arn)

    if resource_summary.resource_type == "role":
        await IAMRole.get(
            tenant,
            resource_summary.account,
            resource_summary.arn,
            force_refresh=force_refresh,
        )


async def update_autogenerated_policy_change_model(
    tenant: str,
    principal_arn: str,
    change: Union[
        InlinePolicyChangeModel,
        PolicyCondenserChangeModel,
        ResourcePolicyChangeModel,
    ],
    source_policy: dict,
    user: str,
    expiration_date,
):
    is_sts_change = bool(change.change_type == "sts_resource_policy")
    if is_sts_change:
        # Maybe allow admin to define full list of policies to trust or not trust in config
        supported_trust_policy_permissions = config.get_tenant_specific_key(
            "policies.supported_trust_policy_permissions",
            tenant,
            [
                "sts:assumerole",
                "sts:tagsession",
                "sts:assumerolewithsaml",
                "sts:assumerolewithwebidentity",
            ],
        )
        if isinstance(supported_trust_policy_permissions, str):
            supported_trust_policy_permissions = [
                supported_trust_policy_permissions.lower()
            ]
        elif isinstance(supported_trust_policy_permissions, list):
            supported_trust_policy_permissions = [
                pp.lower() for pp in supported_trust_policy_permissions
            ]
        else:
            supported_trust_policy_permissions = []
    else:
        supported_trust_policy_permissions = []

    resource_arns = set()
    actions = set()

    for statement in source_policy.get("Statement", []):
        # Find the specific statement within the inline policy associated with this resource
        resources = statement.get("Resource")
        if isinstance(resources, str):
            resources = [resources]

        for resource in resources:
            if change.arn not in resource:
                continue

            resource_arns.add(resource)

            # Use the resource it hit on to catch thing like S3 Bucket + Object
            source_summary = await ResourceSummary.set(tenant, resource)
            service = source_summary.service if not is_sts_change else "sts"
            supported_permissions = get_supported_resource_permissions(
                service, source_summary.resource_type
            )
            # This way we can hit on intended actions and correct any case inconsistencies
            perm_map = {
                f"{service}:{perm.lower()}": f"{service}:{perm}"
                for perm in supported_permissions
            }
            statement_actions = statement.get("Action", [])
            # Normalize statement actions into a list
            statement_actions = (
                statement_actions
                if isinstance(statement_actions, list)
                else [statement_actions]
            )
            for action in statement_actions:
                action = action.lower()
                if resource_action := perm_map.get(action):
                    if (
                        is_sts_change
                        and action not in supported_trust_policy_permissions
                    ):
                        continue
                    actions.add(resource_action)

    resource_sid = await generate_policy_sid(user, expiration_date)
    new_policy = await generate_updated_resource_policy(
        existing=change.old_policy.policy_document,
        principal_arn=principal_arn,
        resource_arns=list(resource_arns),
        actions=list(actions),
        policy_sid=resource_sid,
        # since iam assume role policy documents can't include resources
        include_resources=change.change_type == "resource_policy",
    )
    new_policy_sha256 = sha256(json.dumps(new_policy).encode()).hexdigest()
    change.policy = PolicyModel(
        policy_sha256=new_policy_sha256, policy_document=new_policy
    )


async def generate_resource_policies(
    extended_request: ExtendedRequestModel, user: str, tenant: str
):
    """
    Generates the resource policies and adds it to the extended request.
    Note: generating resource policy is only supported for when the principal ARN is a role right now.

    :param extended_request: ExtendedRequestModel
    :param user: username
    :return:
    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": extended_request.principal,
        "request": extended_request.dict(),
        "message": "Generating resource policies",
    }
    log.debug(log_data)

    supported_resource_policies = config.get_tenant_specific_key(
        "policies.supported_resource_types_for_policy_application",
        tenant,
        ["s3", "sqs", "sns"],
    )
    supported_trust_policy_permissions = config.get_tenant_specific_key(
        "policies.supported_trust_policy_permissions",
        tenant,
        [
            "sts:assumerole",
            "sts:tagsession",
            "sts:assumerolewithsaml",
            "sts:assumerolewithwebidentity",
        ],
    )

    if extended_request.principal.principal_type == "AwsResource":
        principal_arn = extended_request.principal.principal_arn
        resource_summary = await ResourceSummary.set(tenant, principal_arn)
        role_account_id = resource_summary.account

        if (
            resource_summary.service != "iam"
            or resource_summary.resource_type != "role"
        ):
            log_data[
                "message"
            ] = "ARN type not supported for generating resource policy changes."
            log.debug(log_data)
            return extended_request

        resource_policy = {"Version": "2012-10-17", "Statement": [], "Sid": ""}
        resource_policy_sha = sha256(json.dumps(resource_policy).encode()).hexdigest()
        if not resource_summary.resource_type or not resource_summary.service:
            return extended_request

        primary_principal_resource_model = ResourceModel(
            arn=principal_arn,
            name=resource_summary.name,
            account_id=role_account_id,
            resource_type=resource_summary.service,
        )

        auto_generated_resource_policy_changes = []
        # Create resource policy stubs for current resources that are used
        for policy_change in extended_request.changes.changes:
            if policy_change.change_type == "inline_policy":
                policy_change.resources = await get_resources_from_policy_change(
                    policy_change, tenant
                )
                for resource in policy_change.resources:
                    resource_account_id = await ResourceAccountCache.get(
                        tenant, resource.arn
                    )
                    if (
                        resource_account_id != role_account_id
                        and resource.resource_type in supported_resource_policies
                    ):
                        # Cross account
                        auto_generated_resource_policy_changes.append(
                            ResourcePolicyChangeModel(
                                arn=resource.arn,
                                policy=PolicyModel(
                                    policy_document=resource_policy,
                                    policy_sha256=resource_policy_sha,
                                ),
                                change_type="resource_policy",
                                principal=extended_request.principal,
                                status=Status.not_applied,
                                source_change_id=policy_change.id,
                                id=str(uuid.uuid4()),
                                resources=[primary_principal_resource_model],
                                autogenerated=True,
                            )
                        )
                    elif resource.resource_type == "iam":
                        resource_added = False
                        for statement in policy_change.policy.policy_document.get(
                            "Statement", []
                        ):
                            if resource.arn in statement.get("Resource"):
                                # check if action includes supported trust policy permissions
                                statement_actions = statement.get("Action", [])
                                statement_actions = (
                                    statement_actions
                                    if isinstance(statement_actions, list)
                                    else [statement_actions]
                                )
                                for action in statement_actions:
                                    if (
                                        action.lower()
                                        in supported_trust_policy_permissions
                                    ):
                                        # Cross account sts policy
                                        auto_generated_resource_policy_changes.append(
                                            ResourcePolicyChangeModel(
                                                arn=resource.arn,
                                                policy=PolicyModel(
                                                    policy_document=resource_policy,
                                                    policy_sha256=resource_policy_sha,
                                                ),
                                                change_type="sts_resource_policy",
                                                principal=extended_request.principal,
                                                status=Status.not_applied,
                                                source_change_id=policy_change.id,
                                                id=str(uuid.uuid4()),
                                                resources=[
                                                    primary_principal_resource_model
                                                ],
                                                autogenerated=True,
                                            )
                                        )
                                        resource_added = True
                                        break
                            if resource_added:
                                break

        extended_request.changes.changes.extend(auto_generated_resource_policy_changes)
        if len(auto_generated_resource_policy_changes) > 0:
            extended_request.cross_account = True
        log_data["message"] = "Finished generating resource policies"
        log_data["request"] = extended_request.dict()
        log.debug(log_data)
        return extended_request


async def validate_inline_policy_change(
    change: Union[InlinePolicyChangeModel, PolicyCondenserChangeModel],
    user: str,
    role: ExtendedAwsPrincipalModel,
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "policy_name": change.policy_name,
        "request": change.dict(),
        "message": "Validating inline policy change",
    }
    log.debug(log_data)
    if (
        await invalid_characters_in_policy(change.policy.policy_document)
        or await invalid_characters_in_policy(change.policy_name)
        or await invalid_characters_in_policy(change.policy.version)
    ):
        log_data["message"] = "Invalid characters were detected in the policy."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if isinstance(change, PolicyCondenserChangeModel):
        return

    # Can't detach a new policy
    if change.new and change.action == Action.detach:
        log_data["message"] = "Can't detach an inline policy that is new."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    seen_policy_name = False

    for existing_policy in role.inline_policies:
        # Check if a new policy is being created, ensure that we don't overwrite another policy with same name
        if change.new and change.policy_name == existing_policy.get("PolicyName"):
            log_data[
                "message"
            ] = f"Inline Policy with the name {change.policy_name} already exists."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        # Check if policy being updated is the same as existing policy but only if auto_merge is not enabled
        if (
            not change.auto_merge
            and not change.new
            and change.policy.policy_document == existing_policy.get("PolicyDocument")
            and change.policy_name == existing_policy.get("PolicyName")
            and change.action == Action.attach
        ):
            log_data[
                "message"
            ] = f"No changes were found between the updated and existing policy for policy {change.policy_name}."
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])
        if change.policy_name == existing_policy.get("PolicyName"):
            seen_policy_name = True

    # Trying to detach inline policy with name that isn't attached
    if change.action == Action.detach and not seen_policy_name:
        log_data[
            "message"
        ] = f"An inline policy named '{seen_policy_name}' is not attached, so we cannot remove it"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if change.action == Action.attach and not seen_policy_name and not change.new:
        log_data[
            "message"
        ] = f"Inline policy {change.policy_name} not seen but request claims change is not new"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    # TODO: check sha in the request (future feature)
    # If here, then that means inline policy is validated


async def validate_permissions_boundary_change(
    change: PermissionsBoundaryChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating permissions boundary change",
    }
    log.info(log_data)
    policy_name = change.arn.split("/")[-1]
    if await invalid_characters_in_policy(policy_name):
        log_data["message"] = "Invalid characters were detected in the policy name."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    if change.action == Action.attach:
        if not role.permissions_boundary:
            return
        log_data["message"] = (
            "A permissions boundary is already attached to this role. "
            "Only one permission boundary can be attached to a role."
        )
        log.error(log_data)
        raise InvalidRequestParameter(
            "A permissions boundary is already attached to this role. "
            "Only one permission boundary can be attached to a role."
        )
    elif change.action == Action.detach:
        # check to make sure permissions boundary is actually attached to the role
        if change.arn == role.permissions_boundary.get("PermissionsBoundaryArn"):
            return
        log_data[
            "message"
        ] = "The Permissions Boundary you are trying to detach is not attached to this role."
        log.error(log_data)
        raise InvalidRequestParameter(
            f"{change.arn} is not attached to this role as a permissions boundary"
        )


async def validate_managed_policy_change(
    change: ManagedPolicyChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating managed policy change",
    }
    log.info(log_data)
    policy_name = change.arn.split("/")[-1]
    if await invalid_characters_in_policy(policy_name):
        log_data["message"] = "Invalid characters were detected in the policy name."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    if change.action == Action.attach:
        # check to make sure managed policy is not already attached
        for existing_policy in role.managed_policies:
            if change.arn == existing_policy.get("PolicyArn"):
                log_data[
                    "message"
                ] = "Managed Policy with that ARN already attached to this role."
                log.error(log_data)
                raise InvalidRequestParameter(
                    f"{change.arn} already attached to this role"
                )
    elif change.action == Action.detach:
        # check to make sure managed policy is actually attached to role
        seen = False
        for existing_policy in role.managed_policies:
            if change.arn == existing_policy.get("PolicyArn"):
                seen = True
                break
        if not seen:
            log_data[
                "message"
            ] = "The Managed Policy you are trying to detach is not attached to this role."
            log.error(log_data)
            raise InvalidRequestParameter(f"{change.arn} is not attached to this role")

    # TODO: check policy name is same what ARN claims


async def validate_managed_policy_resource_change(
    change: ManagedPolicyResourceChangeModel,
    policy_name: str,
    user: str,
    managed_policy_resource: Dict,
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating managed policy resource change",
    }
    log.info(log_data)
    if await invalid_characters_in_policy(
        policy_name
    ) or await invalid_characters_in_policy(change.policy.policy_document):
        log_data[
            "message"
        ] = "Invalid characters were detected in the policy name or document."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if change.new and managed_policy_resource:
        # change is claiming to be a new policy, but it already exists in AWS
        log_data["message"] = "Managed policy with that ARN already exists"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])
    elif not change.new and not managed_policy_resource:
        # change is claiming to update policy, but it doesn't exist in AWS
        log_data["message"] = "Managed policy with that ARN doesn't exist"
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    if not change.new:
        if change.policy.policy_document == managed_policy_resource:
            log_data[
                "message"
            ] = "No changes detected between current and proposed policy"
            log.error(log_data)
            raise InvalidRequestParameter(log_data["message"])


async def validate_resource_tag_change(
    change: ResourceTagChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "role": role,
        "message": "Validating resource tag change",
    }
    log.debug(log_data)
    # TODO: Add validation here
    return


async def validate_assume_role_policy_change(
    change: AssumeRolePolicyChangeModel, user: str, role: ExtendedAwsPrincipalModel
):
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": change.principal.dict(),
        "request": change.dict(),
        "message": "Validating assume role policy change",
    }
    log.debug(log_data)
    if await invalid_characters_in_policy(
        change.policy.policy_document
    ) or await invalid_characters_in_policy(change.policy.version):
        log_data["message"] = "Invalid characters were detected in the policy."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])

    # Check if policy being updated is the same as existing policy.
    if change.policy.policy_document == role.assume_role_policy_document:
        log_data[
            "message"
        ] = "No changes were found between the updated and existing assume role policy."
        log.error(log_data)
        raise InvalidRequestParameter(log_data["message"])


async def apply_policy_condenser_change(
    resource_summary: ResourceSummary,
    change: PolicyCondenserChangeModel,
    response: PolicyRequestModificationResponseModel,
    iam_client,
    log_data: dict = None,
) -> PolicyRequestModificationResponseModel:
    name = resource_summary.name
    resource_type = resource_summary.resource_type
    assert resource_type in ["user", "role"]
    log_data = log_data or {}
    try:
        boto_params = {f"{resource_type.title()}Name": name}
        list_policies_call = getattr(iam_client, f"list_{resource_type}_policies")
        put_policy_call = getattr(iam_client, f"put_{resource_type}_policy")
        delete_policy_call = getattr(iam_client, f"delete_{resource_type}_policy")

        existing_policies = await aio_wrapper(list_policies_call, **boto_params)
        log_data[
            "message"
        ] = f"Creating new policy for {name} as part of policy_condenser change {change.id}"
        log.debug(log_data)
        # Handle an empty policy document
        if change.policy.policy_document != {"Statement": []}:
            await aio_wrapper(
                put_policy_call,
                PolicyName=change.policy_name,
                PolicyDocument=json.dumps(
                    change.policy.policy_document,
                ),
                **boto_params,
            )
        else:
            log_data[
                "message"
            ] = "Empty policy document was submitted in the change request, skipping policy creation."
            log.debug(log_data)
        for policy in existing_policies.get("PolicyNames", []):
            log_data[
                "message"
            ] = f"Removing policy {policy} from {name} as part of policy_condenser"
            log.debug(log_data)
            await aio_wrapper(delete_policy_call, PolicyName=policy, **boto_params)

        if change.detach_managed_policies:
            detach_managed_policy_call = getattr(
                iam_client, f"detach_{resource_type}_policy"
            )
            managed_policies = await aio_list_managed_policies_for_resource(
                resource_type, name, iam_client
            )
            for managed_policy in managed_policies:
                policy = managed_policy["PolicyArn"]
                log_data[
                    "message"
                ] = f"Detaching managed policy {policy} from {name} as part of policy_condenser"
                log.debug(log_data)
                await aio_wrapper(
                    detach_managed_policy_call,
                    PolicyArn=policy,
                    **boto_params,
                )

        response.action_results.append(
            ActionResult(
                status="success",
                message=(
                    f"Successfully condensed inline policies from principal: " f"{name}"
                ),
            )
        )
        change.status = Status.applied
    except Exception as e:
        log_data["message"] = "Exception occurred condensing inline policies"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=(
                    f"Error occurred condensing inline policies from principal: "
                    f"{resource_summary.name} {str(e)}"
                ),
            )
        )
    finally:
        return response


async def apply_changes_to_role(
    extended_request: ExtendedRequestModel,
    response: Union[RequestCreationResponse, PolicyRequestModificationResponseModel],
    user: str,
    tenant: str,
    specific_change_id: str = None,
    custom_aws_credentials: AWSCredentials = None,
) -> None:
    """
    Applies changes based on the changes array in the request, in a best effort manner to a role

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse
    :param specific_change_id: if this function is being used to apply only one specific change
            if not provided, all non-autogenerated, supported changes are applied
    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "request": extended_request.dict(),
        "message": "Applying request changes",
        "specific_change_id": specific_change_id,
        "tenant": tenant,
    }
    log.info(log_data)

    resource_summary = await ResourceSummary.set(
        tenant, extended_request.principal.principal_arn
    )
    log_data["resource"] = {
        "resource_type": resource_summary.resource_type,
        "service": resource_summary.service,
        "name": resource_summary.name,
    }

    # Principal ARN must be a role for this function
    if resource_summary.service != "iam" or resource_summary.resource_type not in [
        "role",
        "user",
    ]:
        log_data[
            "message"
        ] = "Resource not found, or ARN type not supported for inline/managed/assume role policy changes."
        log.error(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(status="error", message=log_data["message"])
        )
        return

    principal_name = resource_summary.name
    account_id = resource_summary.account
    iam_client = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        tenant,
        user,
        service_type="client",
        account_number=account_id,
        region=config.region,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        session_name=sanitize_session_name("noq_principal_updater_" + user),
        retry_max_attempts=2,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        custom_aws_credentials=custom_aws_credentials,
    )
    for change in extended_request.changes.changes:
        if change.status == Status.applied:
            # This change has already been applied, this can happen in the future when we have a multi-change request
            # that an admin approves, and it applies 5 of the changes, but fails to apply 1 change due to an error.
            # Upon correcting the error, the admin can click approve again, and it will only apply the changes that
            # haven't already been applied
            log_data[
                "message"
            ] = "Change has already been applied, skipping applying the change"
            log_data["change"] = change.dict()
            log.debug(log_data)
            continue
        if specific_change_id and change.id != specific_change_id:
            continue
        if change.change_type == "inline_policy":
            if change.action == Action.attach:
                if change.policy.policy_document != {"Statement": []}:
                    try:
                        if resource_summary.resource_type == "role":
                            await aio_wrapper(
                                iam_client.put_role_policy,
                                RoleName=principal_name,
                                PolicyName=change.policy_name,
                                PolicyDocument=json.dumps(
                                    change.policy.policy_document,
                                ),
                            )
                        elif resource_summary.resource_type == "user":
                            await aio_wrapper(
                                iam_client.put_user_policy,
                                UserName=principal_name,
                                PolicyName=change.policy_name,
                                PolicyDocument=json.dumps(
                                    change.policy.policy_document,
                                ),
                            )
                        response.action_results.append(
                            ActionResult(
                                status="success",
                                message=(
                                    f"Successfully applied inline policy {change.policy_name} to principal: "
                                    f"{principal_name}"
                                ),
                            )
                        )
                        change.status = Status.applied
                    except Exception as e:
                        log_data[
                            "message"
                        ] = "Exception occurred applying inline policy"
                        log_data["error"] = str(e)
                        log.error(log_data, exc_info=True)
                        sentry_sdk.capture_exception()
                        response.errors += 1
                        response.action_results.append(
                            ActionResult(
                                status="error",
                                message=(
                                    f"Error occurred applying inline policy {change.policy_name} to principal: "
                                    f"{principal_name}: " + str(e)
                                ),
                            )
                        )
            elif change.action == Action.detach:
                try:
                    if resource_summary.resource_type == "role":
                        await aio_wrapper(
                            iam_client.delete_role_policy,
                            RoleName=principal_name,
                            PolicyName=change.policy_name,
                        )
                    elif resource_summary.resource_type == "user":
                        await aio_wrapper(
                            iam_client.delete_user_policy,
                            UserName=principal_name,
                            PolicyName=change.policy_name,
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully deleted inline policy {change.policy_name} from principal: "
                                f"{principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred deleting inline policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred deleting inline policy {change.policy_name} from principal: "
                                f"{principal_name} " + str(e)
                            ),
                        )
                    )
        elif change.change_type == "policy_condenser":
            response = await apply_policy_condenser_change(
                resource_summary, change, response, iam_client, log_data
            )
        elif change.change_type == "permissions_boundary":
            if change.action == Action.attach:
                try:
                    if resource_summary.resource_type == "role":
                        await aio_wrapper(
                            iam_client.put_role_permissions_boundary,
                            RoleName=principal_name,
                            PermissionsBoundary=change.arn,
                        )
                    elif resource_summary.resource_type == "user":
                        await aio_wrapper(
                            iam_client.put_user_permissions_boundary,
                            UserName=principal_name,
                            PermissionsBoundary=change.arn,
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully attached permissions boundary {change.arn} to principal: "
                                f"{principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data[
                        "message"
                    ] = "Exception occurred attaching permissions boundary"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred attaching permissions boundary {change.arn} to principal: "
                                f"{principal_name}: " + str(e)
                            ),
                        )
                    )
            elif change.action == Action.detach:
                try:
                    if resource_summary.resource_type == "role":
                        await aio_wrapper(
                            iam_client.delete_role_permissions_boundary,
                            RoleName=principal_name,
                        )
                    elif resource_summary.resource_type == "user":
                        await aio_wrapper(
                            iam_client.delete_user_permissions_boundary,
                            UserName=principal_name,
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully detached permissions boundary {change.arn} from principal: "
                                f"{principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data[
                        "message"
                    ] = "Exception occurred detaching permissions boundary"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred detaching permissions boundary {change.arn} "
                                f"from principal: {principal_name}: " + str(e)
                            ),
                        )
                    )
        elif change.change_type == "managed_policy":
            if change.action == Action.attach:
                try:
                    if resource_summary.resource_type == "role":
                        await aio_wrapper(
                            iam_client.attach_role_policy,
                            RoleName=principal_name,
                            PolicyArn=change.arn,
                        )
                    elif resource_summary.resource_type == "user":
                        await aio_wrapper(
                            iam_client.attach_user_policy,
                            UserName=principal_name,
                            PolicyArn=change.arn,
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully attached managed policy {change.arn} to principal: {principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred attaching managed policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred attaching managed policy {change.arn} to principal: "
                                "{principal_name}: " + str(e)
                            ),
                        )
                    )
            elif change.action == Action.detach:
                try:
                    if resource_summary.resource_type == "role":
                        await aio_wrapper(
                            iam_client.detach_role_policy,
                            RoleName=principal_name,
                            PolicyArn=change.arn,
                        )
                    elif resource_summary.resource_type == "user":
                        await aio_wrapper(
                            iam_client.detach_user_policy,
                            UserName=principal_name,
                            PolicyArn=change.arn,
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=(
                                f"Successfully detached managed policy {change.arn} from principal: {principal_name}"
                            ),
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred detaching managed policy"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=(
                                f"Error occurred detaching managed policy {change.arn} from principal: "
                                f"{principal_name}: " + str(e)
                            ),
                        )
                    )
        elif change.change_type == "assume_role_policy":
            if resource_summary.resource_type == "user":
                raise UnsupportedChangeType(
                    "IAM users don't have assume role policies. Unable to process request."
                )
            try:
                await aio_wrapper(
                    iam_client.update_assume_role_policy,
                    RoleName=principal_name,
                    PolicyDocument=json.dumps(change.policy.policy_document),
                )
                response.action_results.append(
                    ActionResult(
                        status="success",
                        message=f"Successfully updated assume role policy for principal: {principal_name}",
                    )
                )
                change.status = Status.applied
            except Exception as e:
                log_data[
                    "message"
                ] = "Exception occurred updating assume role policy policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()
                response.errors += 1
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=f"Error occurred updating assume role policy for principal: {principal_name}: "
                        + str(e),
                    )
                )
        elif change.change_type == "resource_tag":
            if change.tag_action in [TagAction.create, TagAction.update]:
                if change.original_key and not change.key:
                    change.key = change.original_key
                if change.original_value and not change.value:
                    change.value = change.original_value
                try:
                    if resource_summary.resource_type == "role":
                        await aio_wrapper(
                            iam_client.tag_role,
                            RoleName=principal_name,
                            Tags=[{"Key": change.key, "Value": change.value}],
                        )
                    elif resource_summary.resource_type == "user":
                        await aio_wrapper(
                            iam_client.tag_user,
                            UserName=principal_name,
                            Tags=[{"Key": change.key, "Value": change.value}],
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully created or updated tag for principal: {principal_name}",
                        )
                    )
                    if change.original_key and change.original_key != change.key:
                        if resource_summary.resource_type == "role":
                            await aio_wrapper(
                                iam_client.untag_role,
                                RoleName=principal_name,
                                TagKeys=[change.original_key],
                            )
                        elif resource_summary.resource_type == "user":
                            await aio_wrapper(
                                iam_client.untag_user,
                                UserName=principal_name,
                                TagKeys=[change.original_key],
                            )
                        response.action_results.append(
                            ActionResult(
                                status="success",
                                message=f"Successfully renamed tag {change.original_key} to {change.key}.",
                            )
                        )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred creating or updating tag"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred updating tag for principal: {principal_name}: "
                            + str(e),
                        )
                    )
            if change.tag_action == TagAction.delete:
                try:
                    if resource_summary.resource_type == "role":
                        await aio_wrapper(
                            iam_client.untag_role,
                            RoleName=principal_name,
                            TagKeys=[change.key],
                        )
                    elif resource_summary.resource_type == "user":
                        await aio_wrapper(
                            iam_client.untag_user,
                            UserName=principal_name,
                            TagKeys=[change.key],
                        )
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"Successfully deleted tag for principal: {principal_name}",
                        )
                    )
                    change.status = Status.applied
                except Exception as e:
                    log_data["message"] = "Exception occurred deleting tag"
                    log_data["error"] = str(e)
                    log.error(log_data, exc_info=True)
                    sentry_sdk.capture_exception()
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Error occurred deleting tag for principal: {principal_name}: "
                            + str(e),
                        )
                    )
        else:
            # unsupported type for auto-application
            if change.autogenerated and extended_request.admin_auto_approve:
                # If the change was auto-generated and an administrator auto-approved the choices, there's no need
                # to try to apply the auto-generated policies.
                pass
            else:
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=f"Error occurred applying: Change type {change.change_type} is not supported",
                    )
                )
                response.errors += 1
                log_data["message"] = "Unsupported type for auto-application detected"
                log_data["change"] = change.dict()
                log.error(log_data)

    log_data["message"] = "Finished applying request changes"
    log_data["request"] = extended_request.dict()
    log_data["response"] = response.dict()
    log.info(log_data)


async def populate_old_policies(
    extended_request: ExtendedRequestModel,
    user: str,
    tenant: str,
    principal: Optional[ExtendedAwsPrincipalModel] = None,
    force_refresh=False,
    update=False,
) -> ExtendedRequestModel:
    """
    Populates the old policies for each inline policy.
    Note: Currently only applicable when the principal ARN is a role and for old inline_policies, assume role policy

    :param extended_request: ExtendedRequestModel
    :param user: username
    :return ExtendedRequestModel
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": extended_request.principal,
        "request": extended_request.dict(),
        "message": "Populating old policies",
        "tenant": tenant,
    }
    log.debug(log_data)

    if (
        extended_request.principal.principal_type == "AwsResource"
        and extended_request.principal.principal_arn
    ):
        principal_arn = extended_request.principal.principal_arn
        resource_summary = await ResourceSummary.set(tenant, principal_arn)
        role_account_id = resource_summary.account

        if resource_summary.service != "iam" or resource_summary.resource_type not in [
            "role",
            "user",
        ]:
            log_data[
                "message"
            ] = "ARN type not supported for populating old policy changes."
            log.debug(log_data)
            return extended_request

        principal_name = resource_summary.name
        if not principal:
            if resource_summary.resource_type == "role":
                principal = await get_role_details(
                    role_account_id,
                    principal_name,
                    tenant,
                    extended=True,
                    force_refresh=force_refresh,
                )
            elif resource_summary.resource_type == "user":
                principal = await get_user_details(
                    role_account_id,
                    principal_name,
                    tenant,
                    extended=True,
                    force_refresh=force_refresh,
                )

    for change in extended_request.changes.changes:
        if change.status == Status.applied:
            # Skip changing any old policies that are saved for historical record (already applied)
            continue
        if change.change_type == "assume_role_policy":
            change.old_policy = PolicyModel(
                policy_sha256=sha256(
                    json.dumps(
                        principal.assume_role_policy_document,
                    ).encode()
                ).hexdigest(),
                policy_document=principal.assume_role_policy_document,
            )
        elif change.change_type == "inline_policy" and not change.new:
            for existing_policy in principal.inline_policies:
                if change.policy_name == existing_policy.get("PolicyName"):
                    change.old_policy = PolicyModel(
                        policy_sha256=sha256(
                            json.dumps(
                                existing_policy.get("PolicyDocument"),
                            ).encode()
                        ).hexdigest(),
                        policy_document=existing_policy.get("PolicyDocument"),
                    )
                    break
        elif change.change_type == "policy_condenser":
            combined_policies_document = dict(Statement=[])
            combined_policies = principal.inline_policies
            if change.remove_unused_permissions:
                if change.detach_managed_policies:
                    iam_client = get_tenant_iam_conn(
                        tenant, role_account_id, "noq_get_managed_policy_docs"
                    )
                    sem = NoqSemaphore(aio_get_managed_policy_document, batch_size=20)
                    combined_policies.extend(
                        await sem.process(
                            [
                                {
                                    "policy_arn": policy["PolicyArn"],
                                    "iam_client": iam_client,
                                }
                                for policy in principal.managed_policies
                            ]
                        )
                    )

                for existing_policy in combined_policies:
                    existing_policy = existing_policy.get("PolicyDocument", {})
                    if version := existing_policy.get("Version"):
                        combined_policies_document.setdefault("Version", version)
                    combined_policies_document["Statement"].extend(
                        existing_policy.get("Statement", [])
                    )

                change.old_policy = PolicyModel(
                    policy_sha256=sha256(
                        json.dumps(
                            combined_policies_document,
                        ).encode()
                    ).hexdigest(),
                    policy_document=combined_policies_document,
                )
            elif not change.old_policy:
                change.old_policy = change.policy

    log_data["message"] = "Done populating old policies"
    log_data["request"] = extended_request.dict()
    log.debug(log_data)
    return extended_request


async def populate_old_managed_policies(
    extended_request: ExtendedRequestModel,
    user: str,
    tenant: str,
) -> Dict:
    """
    Populates the old policies for a managed policy resource change.

    :param extended_request: ExtendedRequestModel
    :param user: username
    :return ExtendedRequestModel
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "principal": extended_request.principal,
        "request": extended_request.dict(),
        "message": "Populating old managed policies",
    }
    log.debug(log_data)
    result = {"changed": False}

    if (
        extended_request.principal.principal_type == "AwsResource"
        and extended_request.principal.principal_arn
    ):
        principal_arn = extended_request.principal.principal_arn
        resource_summary = await ResourceSummary.set(tenant, principal_arn)

        if (
            resource_summary.service != "iam"
            or resource_summary.resource_type != "policy"
        ):
            log_data[
                "message"
            ] = "ARN type not supported for populating old managed policy changes."
            log.debug(log_data)
            return result

        try:
            managed_policy_resource = await aio_wrapper(
                get_managed_policy_document,
                tenant=tenant,
                policy_arn=principal_arn,
                account_number=resource_summary.account,
                assume_role=ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", tenant)
                .with_query({"account_id": resource_summary.account})
                .first.name,
                region=config.region,
                retry_max_attempts=2,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                # Could be a new managed policy, hence not found, in this case there are no old policies
                return result
            raise
    else:
        # TODO: Add Honeybee Support for editing managed policies
        return result
    for change in extended_request.changes.changes:
        if (
            change.status == Status.applied
            or change.change_type != "managed_policy_resource"
        ):
            # Skip changing any old policies that are saved for historical record (already applied)
            continue
        if managed_policy_resource:
            old_policy_sha256 = sha256(
                json.dumps(managed_policy_resource).encode()
            ).hexdigest()
            if (
                change.old_policy
                and old_policy_sha256 == change.old_policy.policy_sha256
            ):
                # Old policy hasn't changed since last refresh of page, no need to generate resource policy again
                continue

            result["changed"] = True
            change.old_policy = PolicyModel(
                policy_sha256=sha256(
                    json.dumps(
                        managed_policy_resource,
                    ).encode()
                ).hexdigest(),
                policy_document=managed_policy_resource,
            )

    log_data["message"] = "Done populating old managed policies"
    log_data["request"] = extended_request.dict()
    log.debug(log_data)
    result["extended_request"] = extended_request
    return result


async def populate_cross_account_resource_policy_for_change(
    change, extended_request, log_data, tenant: str, user, force_refresh: bool = False
) -> bool:
    """
    This function generates the action resource (or sts Assume Role Trust) policies associated with a policy
    request. This modifies extended_request in memory, and returns a boolean.
    """
    resource_policies_changed = False
    # TODO: Update this list to fully formed resources instead of the service. e.g. s3:bucket, sqs:queue, sns:topic
    #   This will require refactor for all things that reference this.
    supported_resource_policies = config.get_tenant_specific_key(
        "policies.supported_resource_types_for_policy_application",
        tenant,
        ["s3", "sqs", "sns"],
    )
    sts_resource_policy_supported = config.get_tenant_specific_key(
        "policies.sts_resource_policy_supported", tenant, True
    )
    all_accounts = await get_account_id_to_name_mapping(tenant, status=None)
    default_policy = {"Version": "2012-10-17", "Statement": []}
    if change.status == Status.applied:
        # Skip any changes that have already been applied so we don't overwrite any historical records
        return resource_policies_changed
    if (
        change.change_type == "resource_policy"
        or change.change_type == "sts_resource_policy"
    ):
        try:
            resource_summary = await ResourceSummary.set(
                tenant, change.arn, region_required=True
            )
        except ValueError:
            change.supported = False
            old_policy = default_policy
            log_data["message"] = "Resource account couldn't be determined"
            log_data["resource_arn"] = change.arn
            log.warning(log_data)
        else:
            # Right now supported_resource_policies is actually the service
            if resource_summary.service in supported_resource_policies:
                change.supported = True
            elif (
                change.change_type == "sts_resource_policy"
                and sts_resource_policy_supported
            ):
                change.supported = True
            else:
                change.supported = False

            if resource_summary.account not in all_accounts.keys():
                # if we see the resource account, but it is not an account that we own
                change.supported = False
                old_policy = default_policy
                log_data[
                    "message"
                ] = "Resource account doesn't belong to organization's accounts"
                log_data["resource_arn"] = change.arn
                log.warning(log_data)
            else:
                if change.change_type == "resource_policy":
                    old_policy = await get_resource_policy(
                        account=resource_summary.account,
                        resource_type=resource_summary.service,
                        name=resource_summary.name,
                        region=resource_summary.region,
                        tenant=tenant,
                        user=user,
                    )
                else:
                    role = await get_role_details(
                        resource_summary.account,
                        resource_summary.name,
                        tenant,
                        extended=True,
                        force_refresh=force_refresh,
                    )
                    if not role:
                        log.error(
                            {
                                **log_data,
                                "message": (
                                    "Unable to retrieve role. Won't attempt to make cross-account policy."
                                ),
                            }
                        )
                        return False
                    old_policy = role.assume_role_policy_document

        old_policy_sha256 = sha256(json.dumps(old_policy).encode()).hexdigest()
        if change.old_policy and old_policy_sha256 == change.old_policy.policy_sha256:
            # Old policy hasn't changed since last refresh of page, no need to generate resource policy again
            return False
        # It has changed
        resource_policies_changed = True
        change.old_policy = PolicyModel(
            policy_sha256=old_policy_sha256, policy_document=old_policy
        )
        if not change.autogenerated:
            # Change is not autogenerated (user submitted or modified), don't auto-generate
            return resource_policies_changed

        if change.supported and change.source_change_id:
            source_change = [
                sc
                for sc in extended_request.changes.changes
                if sc.id == change.source_change_id
            ]
            if not source_change:
                return False

            await update_autogenerated_policy_change_model(
                tenant=tenant,
                principal_arn=extended_request.principal.principal_arn,
                change=change,
                source_policy=source_change[0].policy.policy_document,
                user=user,
                expiration_date=extended_request.expiration_date,
            )

        return resource_policies_changed


async def populate_cross_account_resource_policies(
    extended_request: ExtendedRequestModel, user: str, tenant: str
) -> Dict:
    """
    Populates the cross-account resource policies for supported resources for each inline policy.
    :param extended_request: ExtendedRequestModel
    :param user: username
    :return: Dict:
        changed: whether the resource policies have changed or not
        extended_request: modified extended_request
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "arn": extended_request.principal.principal_arn,
        "request": extended_request.dict(),
        "message": "Populating cross-account resource policies",
        "tenant": tenant,
    }
    log.debug(log_data)

    concurrent_tasks = []
    for change in extended_request.changes.changes:
        concurrent_tasks.append(
            populate_cross_account_resource_policy_for_change(
                change, extended_request, log_data, tenant, user
            )
        )
    concurrent_tasks_results = await asyncio.gather(*concurrent_tasks)
    resource_policies_changed = bool(any(concurrent_tasks_results))

    log_data["message"] = "Done populating cross account resource policies"
    log_data["request"] = extended_request.dict()
    log_data["resource_policies_changed"] = resource_policies_changed
    log.debug(log_data)
    return {"changed": resource_policies_changed, "extended_request": extended_request}


async def apply_managed_policy_resource_tag_change(
    extended_request: ExtendedRequestModel,
    change: ResourceTagChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
    tenant: str,
    custom_aws_credentials: AWSCredentials = None,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource tagging changes for managed policies

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse

    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying resource policy change changes",
        "request": extended_request.dict(),
    }

    try:
        resource_summary = await ResourceSummary.set(
            tenant, change.principal.principal_arn
        )
        account = resource_summary.account
        resource_type = resource_summary.resource_type
        service = resource_summary.service
    except ValueError:
        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # we can't apply this change
        log_data["message"] = "Resource account not found"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.principal.json()} as cannot determine resource account",
            )
        )
        return response

    if service != "iam" or resource_type != "policy" or account == "aws":
        # Not a managed policy, or a managed policy that is AWS owned
        log_data["message"] = "Resource change not supported"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.principal.json()} as it's not supported",
            )
        )
        return response
    iam_client = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        tenant,
        user,
        service_type="client",
        account_number=account,
        region=config.region,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account})
        .first.name,
        session_name=sanitize_session_name("noq_tag_updater_" + user),
        retry_max_attempts=2,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        custom_aws_credentials=custom_aws_credentials,
    )
    principal_arn = change.principal.principal_arn
    if change.tag_action in [TagAction.create, TagAction.update]:
        if change.original_key and not change.key:
            change.key = change.original_key
        if change.original_value and not change.value:
            change.value = change.original_value
        try:
            await aio_wrapper(
                iam_client.tag_policy,
                PolicyArn=principal_arn,
                Tags=[{"Key": change.key, "Value": change.value}],
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully created or updated tag for managed policy: {principal_arn}",
                )
            )
            if change.original_key and change.original_key != change.key:
                await aio_wrapper(
                    iam_client.untag_policy,
                    PolicyArn=principal_arn,
                    TagKeys=[change.original_key],
                )
                response.action_results.append(
                    ActionResult(
                        status="success",
                        message=f"Successfully renamed tag {change.original_key} to {change.key}.",
                    )
                )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred creating or updating tag"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred updating tag for managed policy: {principal_arn}: "
                    + str(e),
                )
            )
    elif change.tag_action == TagAction.delete:
        try:
            await aio_wrapper(
                iam_client.untag_policy, PolicyArn=principal_arn, TagKeys=[change.key]
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully deleted tag for managed policy: {principal_arn}",
                )
            )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred deleting tag"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred deleting tag for managed policy: {principal_arn}: "
                    + str(e),
                )
            )
    else:
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Unsupport change requested for tag {change.tag_action}",
            )
        )

    return response


async def apply_non_iam_resource_tag_change(
    extended_request: ExtendedRequestModel,
    change: ResourceTagChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
    tenant: str,
    arn: str,
    custom_aws_credentials: AWSCredentials = None,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource tagging changes for supported non IAM role tags

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse

    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying resource policy change changes",
        "request": extended_request.dict(),
    }

    resource_summary = await ResourceSummary.set(tenant, arn)
    account = resource_summary.account
    service = resource_summary.service
    supported_services = config.get_tenant_specific_key(
        "policies.supported_resource_types_for_policy_application",
        tenant,
        ["s3", "sqs", "sns"],
    )

    if service not in supported_services:
        log_data["message"] = "Resource change not supported"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.principal.json()} as it's not supported",
            )
        )
        return response

    try:
        client = await aio_wrapper(
            boto3_cached_conn,
            service,
            tenant,
            user,
            service_type="client",
            future_expiration_minutes=15,
            account_number=account,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account})
            .first.name,
            region=resource_summary.region or config.region,
            session_name=sanitize_session_name("noq_apply_resource_tag_" + user),
            arn_partition="aws",
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            retry_max_attempts=2,
            custom_aws_credentials=custom_aws_credentials,
        )

        resource_details = await fetch_resource_details(
            account,
            service,
            resource_summary.name,
            resource_summary.region or config.region,
            tenant,
            user,
        )

        if change.original_key and not change.key:
            change.key = change.original_key
        if change.original_value and not change.value:
            change.value = change.original_value

        if service == "s3":
            if change.tag_action in [TagAction.create, TagAction.update]:
                tag_key_preexists = False
                resulting_tagset = []
                for tag in resource_details["TagSet"]:
                    # If we renamed a tag key, let's "skip" the tag with the original name
                    if change.original_key and change.original_key != change.key:
                        if tag.get("Key") == change.original_key:
                            continue
                    if change.key == tag["Key"]:
                        tag_key_preexists = True
                        # If we changed the value of an existing tag, let's record that
                        resulting_tagset.append(
                            {"Key": change.key, "Value": change.value}
                        )
                    else:
                        # Leave original tag unmodified
                        resulting_tagset.append(tag)

                # Let's create the tag if it is a new one
                if not tag_key_preexists:
                    resulting_tagset.append({"Key": change.key, "Value": change.value})

                await aio_wrapper(
                    client.put_bucket_tagging,
                    Bucket=resource_summary.name,
                    Tagging={"TagSet": resulting_tagset},
                )

            elif change.tag_action == TagAction.delete:
                resulting_tagset = []

                for tag in resource_details["TagSet"]:
                    if tag.get("Key") != change.key:
                        resulting_tagset.append(tag)

                resource_details["TagSet"] = resulting_tagset
                await aio_wrapper(
                    client.put_bucket_tagging,
                    Bucket=resource_summary.name,
                    Tagging={"TagSet": resource_details["TagSet"]},
                )
        elif service == "sns":
            if change.tag_action in [TagAction.create, TagAction.update]:
                await aio_wrapper(
                    client.tag_resource,
                    ResourceArn=change.principal.principal_arn,
                    Tags=[{"Key": change.key, "Value": change.value}],
                )
                # Renaming a key
                if change.original_key and change.original_key != change.key:
                    await aio_wrapper(
                        client.untag_resource,
                        ResourceArn=change.principal.principal_arn,
                        TagKeys=[change.original_key],
                    )
            elif change.tag_action == TagAction.delete:
                await aio_wrapper(
                    client.untag_resource,
                    ResourceArn=change.principal.principal_arn,
                    TagKeys=[change.key],
                )
        elif service == "sqs":
            if change.tag_action in [TagAction.create, TagAction.update]:
                await aio_wrapper(
                    client.tag_queue,
                    QueueUrl=resource_details["QueueUrl"],
                    Tags={change.key: change.value},
                )
                # Renaming a key
                if change.original_key and change.original_key != change.key:
                    await aio_wrapper(
                        client.untag_queue,
                        QueueUrl=resource_details["QueueUrl"],
                        TagKeys=[change.original_key],
                    )
            elif change.tag_action == TagAction.delete:
                await aio_wrapper(
                    client.untag_queue,
                    QueueUrl=resource_details["QueueUrl"],
                    TagKeys=[change.key],
                )
        response.action_results.append(
            ActionResult(
                status="success",
                message=f"Successfully updated resource policy for {change.principal.principal_arn}",
            )
        )
        change.status = Status.applied

    except Exception as e:
        log_data["message"] = "Exception changing resource tags"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Error occurred changing resource tags for {change.principal.principal_arn}"
                + str(e),
            )
        )

    log_data["message"] = "Finished applying resource tagging change"
    log_data["response"] = response.dict()
    log_data["request"] = extended_request.dict()
    log_data["change"] = change.dict()
    log.debug(log_data)
    return response


async def apply_tra_role_change(
    extended_request: ExtendedRequestModel,
    change: ManagedPolicyResourceChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
    tenant: str,
) -> PolicyRequestModificationResponseModel:
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Granting TRA support to user",
        "request": extended_request.dict(),
        "tenant": tenant,
    }
    log.info(log_data)
    resource_summary = await ResourceSummary.set(
        tenant, extended_request.principal.principal_arn
    )
    account_id = resource_summary.account
    principal_name = resource_summary.name

    try:
        iam_client = await aio_wrapper(
            boto3_cached_conn,
            "iam",
            tenant,
            user,
            service_type="client",
            account_number=account_id,
            region=config.region,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name,
            session_name=sanitize_session_name("noq_principal_updater_" + user),
            retry_max_attempts=2,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
        )
        tra_users_tag = get_active_tra_users_tag(tenant)
        role_tags = await aio_wrapper(
            iam_client.list_role_tags, RoleName=principal_name
        )
        elevated_users = get_resource_tag(role_tags, tra_users_tag, True, set())
        elevated_users.add(user)

        await aio_wrapper(
            iam_client.tag_role,
            RoleName=principal_name,
            Tags=[{"Key": tra_users_tag, "Value": ":".join(elevated_users)}],
        )
        change.status = Status.applied
    except Exception as e:
        log_data["message"] = "Exception occurred creating or updating tag"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Error occurred updating tag for principal: {principal_name}: "
                + str(e),
            )
        )

    return response


async def apply_role_access_change(
    extended_request: ExtendedRequestModel,
    change: RoleAccessChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
    tenant: str,
) -> PolicyRequestModificationResponseModel:
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Updating role access to one or more identity",
        "request": extended_request.dict(),
        "tenant": tenant,
    }
    log.info(log_data)
    resource_summary = await ResourceSummary.set(
        tenant, extended_request.principal.principal_arn
    )
    account_id = resource_summary.account
    principal_name = resource_summary.name
    role_access_tags = config.get_tenant_specific_key(
        "cloud_credential_authorization_mapping.role_tags.authorized_groups_tags",
        tenant,
        [],
    )

    try:
        iam_client = await aio_wrapper(
            boto3_cached_conn,
            "iam",
            tenant,
            user,
            service_type="client",
            account_number=account_id,
            region=config.region,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name,
            session_name=sanitize_session_name("noq_principal_updater_" + user),
            retry_max_attempts=2,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
        )
        role_tags = await aio_wrapper(
            iam_client.list_role_tags, RoleName=principal_name
        )

        if change.action == Action1.add:
            # Add to the default tag and only if the identity is not in any other role access tag
            role_access_tag = role_access_tags[0]
            tag_val = get_resource_tag(role_tags, role_access_tag, True, set())
            identities_with_role_access = set(*tag_val)

            if len(role_tags) > 1:
                for x in range(1, len(role_access_tags)):
                    identities_with_role_access.update(
                        get_resource_tag(role_tags, role_access_tags[x], True, set())
                    )

            for identity in change.identities:
                if identity not in identities_with_role_access:
                    tag_val.add(identity)

            await aio_wrapper(
                iam_client.tag_role,
                RoleName=principal_name,
                Tags=[{"Key": role_access_tag, "Value": ":".join(tag_val)}],
            )
        elif change.action == Action1.remove:
            for role_access_tag in role_access_tags:
                requires_update = False
                tag_val = set()
                role_access_tag_vals = get_resource_tag(
                    role_tags, role_access_tag, True, set()
                )
                for role_access_tag_val in role_access_tag_vals:
                    if any(
                        role_access_tag_val == identity
                        for identity in change.identities
                    ):
                        requires_update = True
                    else:
                        tag_val.add(role_access_tag_val)

                if requires_update:
                    if tag_val:
                        await aio_wrapper(
                            iam_client.tag_role,
                            RoleName=principal_name,
                            Tags=[{"Key": role_access_tag, "Value": ":".join(tag_val)}],
                        )
                    else:
                        await aio_wrapper(
                            iam_client.untag_role,
                            RoleName=principal_name,
                            TagKeys=[role_access_tag],
                        )

        change.status = Status.applied
    except Exception as e:
        log_data["message"] = "Exception occurred creating or updating tag"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Error occurred updating tag for principal: {principal_name}: "
                + str(e),
            )
        )

    return response


async def apply_create_role_change(
    extended_request: ExtendedRequestModel,
    change: CreateResourceChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
    tenant: str,
) -> PolicyRequestModificationResponseModel:
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Creating role",
        "request": extended_request.dict(),
        "tenant": tenant,
    }
    log.info(log_data)
    iam_request = await IAMRequest.get(tenant, extended_request.id)
    iam_role, results = await IAMRole.create(iam_request, change)
    if iam_role:
        change.status = Status.applied

        # Now that the resource exists we can assign an arn where applicable throughout the request
        change.principal.principal_arn = iam_role.arn
        extended_request.principal = change.principal
        for elem in range(len(extended_request.changes.changes)):
            extended_request.changes.changes[elem].principal = change.principal

        iam_request.arn = iam_role.arn
        iam_request.principal = json.loads(change.principal.json())
        iam_request.extended_request = json.loads(extended_request.json())
        iam_request.last_updated = int(time.time())
        await iam_request.save()
    else:
        response.errors += results.get("errors", 1)
        response.action_results.extend(results.get("action_results", []))

    return response


async def apply_managed_policy_resource_change(
    extended_request: ExtendedRequestModel,
    change: ManagedPolicyResourceChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
    tenant: str,
    custom_aws_credentials: AWSCredentials = None,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource policy change for managed policies

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse
    :param tenant: Tenant ID

    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying managed policy resource change",
        "request": extended_request.dict(),
        "tenant": tenant,
    }
    log.info(log_data)

    resource_summary = await ResourceSummary.set(
        tenant, extended_request.principal.principal_arn
    )
    resource_account = resource_summary.account

    if (
        resource_summary.service != "iam"
        or resource_summary.resource_type != "policy"
        or resource_summary.account == "aws"
    ):
        log_data[
            "message"
        ] = "ARN type not supported for managed policy resource changes."
        log.error(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(status="error", message=log_data["message"])
        )
        return response

    if not resource_summary.account:
        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # we can't apply this change
        log_data["message"] = "Resource account not found"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {extended_request.principal.principal_arn} as cannot determine resource account",
            )
        )
        return response

    conn_details = {
        "account_number": resource_account,
        "assume_role": ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": resource_account})
        .first.name,
        "session_name": sanitize_session_name(f"noq_MP_{user}"),
        "client_kwargs": config.get_tenant_specific_key(
            "boto3.client_kwargs", tenant, {}
        ),
        "tenant": tenant,
        "custom_aws_credentials": custom_aws_credentials,
    }

    # Save current policy by populating "old" policies at the time of application for historical record
    populate_old_managed_policies_results = await populate_old_managed_policies(
        extended_request, user, tenant
    )
    if populate_old_managed_policies_results["changed"]:
        extended_request = populate_old_managed_policies_results["extended_request"]

    policy_name = resource_summary.name
    if change.new:
        description = f"Managed Policy created using Noq by {user}"
        # create new policy
        try:
            await create_or_update_managed_policy(
                new_policy=change.policy.policy_document,
                policy_name=policy_name,
                policy_arn=extended_request.principal.principal_arn,
                description=description,
                tenant=tenant,
                conn_details=conn_details,
                policy_path=resource_summary.path,
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully created managed policy {extended_request.principal.principal_arn}",
                )
            )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred creating managed policy"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred creating managed policy: {str(e)}",
                )
            )
    else:
        try:
            await create_or_update_managed_policy(
                new_policy=change.policy.policy_document,
                policy_name=policy_name,
                policy_arn=extended_request.principal.principal_arn,
                description="",
                tenant=tenant,
                conn_details=conn_details,
                policy_path=resource_summary.path,
                existing_policy=True,
            )
            response.action_results.append(
                ActionResult(
                    status="success",
                    message=f"Successfully updated managed policy {extended_request.principal.principal_arn}",
                )
            )
            change.status = Status.applied
        except Exception as e:
            log_data["message"] = "Exception occurred updating managed policy"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            response.errors += 1
            response.action_results.append(
                ActionResult(
                    status="error",
                    message=f"Error occurred creating updating policy: {str(e)}",
                )
            )
    return response


async def apply_resource_policy_change(
    extended_request: ExtendedRequestModel,
    change: ResourcePolicyChangeModel,
    response: PolicyRequestModificationResponseModel,
    user: str,
    tenant: str,
    force_refresh: bool = False,
    custom_aws_credentials: AWSCredentials = None,
) -> PolicyRequestModificationResponseModel:
    """
    Applies resource policy change for supported changes

    Caution: this method applies changes blindly... meaning it assumes before calling this method,
    you have validated the changes being made are authorized.

    :param change: ResourcePolicyChangeModel
    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param response: RequestCreationResponse

    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "change": change.dict(),
        "message": "Applying resource policy change changes",
        "request": extended_request.dict(),
        "tenant": tenant,
    }
    log.info(log_data)

    resource_summary = await ResourceSummary.set(
        tenant, change.arn, region_required=True
    )
    resource_account = resource_summary.account
    resource_region = resource_summary.region

    if not resource_account:
        # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
        # we can't apply this change
        log_data["message"] = "Resource account not found"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.arn} as cannot determine resource account",
            )
        )
        return response

    supported_services = config.get_tenant_specific_key(
        "policies.supported_resource_types_for_policy_application",
        tenant,
        ["s3", "sqs", "sns"],
    )
    sts_resource_policy_supported = config.get_tenant_specific_key(
        "policies.sts_resource_policy_supported", tenant, True
    )

    if (
        not change.supported
        or (
            change.change_type == "resource_policy"
            and resource_summary.service not in supported_services
        )
        or (
            change.change_type == "sts_resource_policy"
            and not sts_resource_policy_supported
        )
    ):
        log_data["message"] = "Resource change not supported"
        log.warning(log_data)
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Cannot apply change to {change.arn} as it's not supported",
            )
        )
        return response

    try:
        client = await aio_wrapper(
            boto3_cached_conn,
            resource_summary.service,
            tenant,
            user,
            service_type="client",
            future_expiration_minutes=15,
            account_number=resource_account,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": resource_account})
            .first.name,
            region=resource_region or config.region,
            session_name=sanitize_session_name("noq_apply_resource_policy-" + user),
            arn_partition="aws",
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            retry_max_attempts=2,
            custom_aws_credentials=custom_aws_credentials,
        )
        if resource_summary.service == "s3":
            await aio_wrapper(
                client.put_bucket_policy,
                Bucket=resource_summary.name,
                Policy=json.dumps(change.policy.policy_document),
            )
        elif resource_summary.service == "sns":
            await aio_wrapper(
                client.set_topic_attributes,
                TopicArn=change.arn,
                AttributeName="Policy",
                AttributeValue=json.dumps(change.policy.policy_document),
            )
        elif resource_summary.service == "sqs":
            queue_url: dict = await aio_wrapper(
                client.get_queue_url, QueueName=resource_summary.name
            )
            await aio_wrapper(
                client.set_queue_attributes,
                QueueUrl=queue_url.get("QueueUrl"),
                Attributes={"Policy": json.dumps(change.policy.policy_document)},
            )
        elif resource_summary.service == "iam":
            role_name = resource_summary.name
            await aio_wrapper(
                client.update_assume_role_policy,
                RoleName=role_name,
                PolicyDocument=json.dumps(change.policy.policy_document),
            )
            await update_resource_in_dynamo(tenant, change.arn, force_refresh)
        response.action_results.append(
            ActionResult(
                status="success",
                message=f"Successfully updated resource policy for {change.arn}",
            )
        )
        change.status = Status.applied

    except Exception as e:
        log_data["message"] = "Exception occurred updating resource policy"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(
                status="error",
                message=f"Error occurred updating resource policy for {change.arn}"
                + str(e),
            )
        )

    log_data["message"] = "Finished applying resource policy change"
    log_data["response"] = response.dict()
    log_data["request"] = extended_request.dict()
    log_data["change"] = change.dict()
    log.debug(log_data)
    return response


async def _add_error_to_response(
    log_data: Dict,
    response: PolicyRequestModificationResponseModel,
    message: str,
    error=None,
):
    log_data["message"] = message
    log_data["error"] = error
    log.error(log_data)
    response.errors += 1
    response.action_results.append(
        ActionResult(status="error", message=log_data["message"])
    )
    return response


async def _update_dynamo_with_change(
    user: str,
    tenant: str,
    extended_request: ExtendedRequestModel,
    log_data: Dict,
    response: PolicyRequestModificationResponseModel,
    success_message: str,
    error_message: str,
    visible: bool = True,
):
    try:
        await IAMRequest.write_v2(extended_request, tenant)
        if visible:
            response.action_results.append(
                ActionResult(status="success", message=success_message)
            )
    except Exception as e:
        log_data["message"] = error_message
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        sentry_sdk.capture_exception()
        response.errors += 1
        response.action_results.append(
            ActionResult(status="error", message=error_message + ": " + str(e))
        )
    return response


async def _get_specific_change(changes: ChangeModelArray, change_id: str):
    for change in changes.changes:
        if change.id == change_id:
            return change

    return None


async def maybe_approve_reject_request(
    extended_request: ExtendedRequestModel,
    user: str,
    log_data: Dict,
    response: PolicyRequestModificationResponseModel,
    tenant: str,
    force_refresh: bool = False,
    auto_approved: bool = False,
) -> PolicyRequestModificationResponseModel:
    any_changes_applied = False
    any_changes_pending = False
    any_changes_cancelled = False
    request_status_changed = False

    for change in extended_request.changes.changes:
        if change.status == Status.applied:
            any_changes_applied = True
        if change.status == Status.not_applied:
            # Don't consider "unsupported" resource policies as "pending", since they can't be applied.
            if (
                change.change_type == "resource_policy"
                or change.change_type == "sts_resource_policy"
            ) and change.supported is False:
                continue
            # Requests should still be marked as approved if they have pending autogenerated changes
            if change.autogenerated:
                continue
            any_changes_pending = True
        if change.status == Status.cancelled:
            any_changes_cancelled = True
    # Automatically mark request as "approved" if at least one of the changes in the request is approved, and
    # nothing else is pending
    if any_changes_applied and not any_changes_pending:
        extended_request.request_status = RequestStatus.approved
        request_status_changed = True

    # Automatically mark request as "cancelled" if all changes in the request are cancelled
    if not any_changes_applied and not any_changes_pending and any_changes_cancelled:
        extended_request.request_status = RequestStatus.cancelled
        request_status_changed = True
    if request_status_changed:
        extended_request.reviewer = user
        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            "Successfully updated request status",
            "Error updating request in dynamo",
            visible=False,
        )
        await send_communications_policy_change_request_v2(
            extended_request, tenant, auto_approved
        )
        if any_changes_applied:
            await update_resource_in_dynamo(
                tenant, extended_request.principal.principal_arn, force_refresh
            )
    return response


async def parse_and_apply_policy_request_modification(
    extended_request: ExtendedRequestModel,
    policy_request_model: PolicyRequestModificationRequestModel,
    user: str,
    user_groups,
    last_updated,
    tenant: str,
    approval_rule_approved=False,
    force_refresh=False,
    cloud_credentials: CloudCredentials = None,
    auto_approved: bool = False,
) -> PolicyRequestModificationResponseModel:
    """
    Parses the policy request modification changes

    :param extended_request: ExtendedRequestModel
    :param user: Str - requester's email address
    :param policy_request_model: PolicyRequestModificationRequestModel
    :param user_groups:  user's groups
    :param last_updated:
    :param approval_rule_approved: Whether this change was approved by an auto-approval rule. If not, user needs to be
        authorized to make the change.
    :param cloud_credentials: User provided credentials
        used to override the default credentials for interfacing with a cloud provider
    :return PolicyRequestModificationResponseModel
    """

    log_data: Dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "request": extended_request.dict(),
        "request_changes": policy_request_model.dict(),
        "message": "Parsing request modification changes",
        "tenant": tenant,
        "auto_approved": auto_approved,
    }

    log.debug(log_data)
    # Validate cloud credentials
    await validate_custom_credentials(
        tenant, extended_request, policy_request_model, cloud_credentials
    )

    response = PolicyRequestModificationResponseModel(errors=0, action_results=[])
    request_changes = policy_request_model.modification_model
    specific_change_arn = None

    if request_changes.command in [Command.update_change, Command.cancel_request]:

        if request_changes.command == Command.update_change:
            update_change_model = UpdateChangeModificationModel.parse_obj(
                request_changes
            )
            specific_change = await _get_specific_change(
                extended_request.changes, update_change_model.change_id
            )
            if not specific_change:
                raise NoMatchingRequest(
                    "Unable to find a compatible non-applied change with "
                    "that ID in this policy request"
                )

            specific_change_arn = specific_change.principal.principal_arn
            if specific_change.change_type in [
                "managed_policy_resource",
                "resource_policy",
                "sts_resource_policy",
            ]:
                specific_change_arn = specific_change.arn

            account_ids = [await ResourceAccountCache.get(tenant, specific_change_arn)]
        else:
            account_ids = await get_extended_request_account_ids(
                extended_request, tenant
            )

        can_update_cancel = await can_update_cancel_requests_v2(
            extended_request, user, user_groups, tenant, account_ids
        )
        if not can_update_cancel:
            raise Unauthorized(
                "You are not authorized to update or cancel changes in this request"
            )

    if request_changes.command in [
        Command.apply_change,
        Command.approve_request,
        Command.reject_request,
    ]:
        if request_changes.command in [Command.approve_request, Command.reject_request]:
            account_ids = await get_extended_request_account_ids(
                extended_request, tenant
            )

        if request_changes.command == Command.apply_change:
            apply_change_model = ApplyChangeModificationModel.parse_obj(request_changes)
            if apply_change_model.apply_all_changes:
                # If apply all changes, then we need to find all changes that are not applied
                # and apply them
                changes_to_apply = [
                    change
                    for change in extended_request.changes.changes
                    if change.status == Status.not_applied
                ]
                # Set supported to true for all changes
                for change in changes_to_apply:
                    change.supported = True
            else:
                changes_to_apply = [
                    await _get_specific_change(
                        extended_request.changes, apply_change_model.change_id
                    )
                ]
            for specific_change in changes_to_apply:
                if not specific_change:
                    raise NoMatchingRequest(
                        "Unable to find a compatible non-applied change with "
                        "that ID in this policy request"
                    )

                specific_change_arn = specific_change.principal.principal_arn
                if specific_change.change_type in [
                    "resource_policy",
                    "sts_resource_policy",
                ]:
                    specific_change_arn = specific_change.arn

                account_id = specific_change.principal.account_id or (
                    await ResourceAccountCache.get(tenant, specific_change_arn)
                )

                can_manage_policy_request = await can_admin_policies(
                    user, user_groups, tenant, [account_id]
                )
                # Authorization required if the policy wasn't approved by an auto-approval rule.
                should_apply_because_auto_approved = (
                    request_changes.command == Command.apply_change
                    and approval_rule_approved
                )

                if (
                    not can_manage_policy_request
                    and not should_apply_because_auto_approved
                ):
                    raise Unauthorized("You are not authorized to manage this request")

    if request_changes.command == Command.move_back_to_pending:
        can_move_back_to_pending = await can_move_back_to_pending_v2(
            extended_request, last_updated, user, user_groups, tenant
        )
        if not can_move_back_to_pending:
            raise Unauthorized("Cannot move this request back to pending")

    # If here, then the person is authorized to make the change they want

    # For cancelled / rejected requests, only moving back to pending, adding comments is permitted
    if extended_request.request_status in [
        RequestStatus.cancelled,
        RequestStatus.rejected,
    ] and request_changes.command not in [
        Command.add_comment,
        Command.move_back_to_pending,
        Command.update_expiration_date,
    ]:
        raise InvalidRequestParameter(
            f"Cannot perform {request_changes.command.value} on "
            f"{extended_request.request_status.value} requests"
        )

    if request_changes.command == Command.add_comment:
        auth = get_plugin_by_name(
            config.get_tenant_specific_key("plugins.auth", tenant, "cmsaas_auth")
        )()
        # TODO: max comment size? prevent spamming?
        comment_model = CommentRequestModificationModel.parse_obj(request_changes)
        user_comment = CommentModel(
            id=str(uuid.uuid4()),
            timestamp=int(time.time()),
            user_email=user,
            user=UserModel(
                email=user,
                extended_info=await auth.get_user_info(user, tenant),
                details_url="",
                photo_url="",
            ),
            last_modified=int(time.time()),
            text=comment_model.comment_text,
        )
        extended_request.comments.append(user_comment)
        success_message = "Successfully added comment"
        error_message = "Error occurred adding comment"
        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            success_message,
            error_message,
        )
        if user == extended_request.requester_email:
            # User who created the request adding a comment, notification should go to reviewers
            await send_communications_new_comment(extended_request, user, tenant)
        else:
            # A reviewer or someone else making the comment, notification should go to original requester
            await send_communications_new_comment(
                extended_request,
                user,
                tenant,
                to_addresses=[extended_request.requester_email],
            )

    elif request_changes.command == Command.update_ttl:
        request_model = TTLRequestModificationModel.parse_obj(request_changes)
        extended_request.expiration_date = None
        extended_request.ttl = request_model.ttl
        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            "Successfully updated the request ttl",
            "Error occurred updating the request ttl",
        )

    elif request_changes.command == Command.update_expiration_date:
        extended_request.ttl = None
        expiration_date_model = ExpirationDateRequestModificationModel.parse_obj(
            request_changes
        )
        if expiration_date_model.expiration_date and isinstance(
            expiration_date_model.expiration_date, str
        ):
            expiration_date_model.expiration_date = parser.parse(
                expiration_date_model.expiration_date
            )
        extended_request = await update_extended_request_expiration_date(
            tenant, user, extended_request, expiration_date_model.expiration_date
        )

        success_message = "Successfully updated expiration date"
        error_message = "Error occurred updating expiration date"
        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            success_message,
            error_message,
        )

    elif request_changes.command == Command.update_change:
        update_change_model = UpdateChangeModificationModel.parse_obj(request_changes)
        specific_change = await _get_specific_change(
            extended_request.changes, update_change_model.change_id
        )
        # We only support updating inline policies, assume role policy documents and resource policies that haven't
        # applied already
        if (
            specific_change
            and specific_change.change_type
            in [
                "inline_policy",
                "policy_condenser",
                "resource_policy",
                "sts_resource_policy",
                "assume_role_policy",
                "managed_policy_resource",
            ]
            and specific_change.status == Status.not_applied
        ):
            specific_change.policy.policy_document = update_change_model.policy_document

            if (
                specific_change.change_type == "resource_policy"
                or specific_change.change_type == "sts_resource_policy"
            ):
                # Special case, if it's autogenerated and a user modifies it, update status to
                # not autogenerated, so we don't overwrite it on page refresh
                specific_change.autogenerated = False
            success_message = "Successfully updated policy document"
            error_message = "Error occurred updating policy document"
            specific_change.updated_by = user
            response = await _update_dynamo_with_change(
                user,
                tenant,
                extended_request,
                log_data,
                response,
                success_message,
                error_message,
            )
        else:
            raise NoMatchingRequest(
                "Unable to find a compatible non-applied change with "
                "that ID in this policy request"
            )

    elif request_changes.command == Command.apply_change:
        custom_aws_credentials: AWSCredentials = (
            None if not cloud_credentials else cloud_credentials.aws
        )

        apply_change_model = ApplyChangeModificationModel.parse_obj(request_changes)
        if apply_change_model.apply_all_changes:
            # If apply all changes, then we need to find all changes that are not applied
            # and apply them
            changes_to_apply = [
                change
                for change in extended_request.changes.changes
                if change.status == Status.not_applied
            ]
        else:
            changes_to_apply = [
                await _get_specific_change(
                    extended_request.changes, apply_change_model.change_id
                )
            ]

        for specific_change in changes_to_apply:
            if specific_change and specific_change.status == Status.not_applied:
                # Update the policy doc locally for supported changes, if it needs to be updated
                if (
                    apply_change_model.policy_document
                    and specific_change.change_type
                    in [
                        "inline_policy",
                        "policy_condenser",
                        "resource_policy",
                        "sts_resource_policy",
                        "assume_role_policy",
                        "managed_policy_resource",
                    ]
                ):
                    specific_change.policy.policy_document = (
                        apply_change_model.policy_document
                    )
                managed_policy_arn_regex = re.compile(r"^arn:aws:iam::\d{12}:policy/.+")

                try:
                    account_info: SpokeAccount = (
                        ModelAdapter(SpokeAccount)
                        .load_config("spoke_accounts", tenant)
                        .with_query({"account_id": account_id})
                        .first
                    )
                except ValueError:
                    # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
                    # we can't apply this change
                    log_data["message"] = "Resource account not found"
                    log.warning(log_data)
                    response.errors += 1
                    response.action_results.append(
                        ActionResult(
                            status="error",
                            message=f"Cannot apply change to {specific_change.principal.json()} as cannot determine resource account",
                        )
                    )
                    return response

                if account_info.read_only and (
                    specific_change.change_type == "tra_can_assume_role"
                    or not cloud_credentials
                ):
                    specific_change.status = Status.applied
                    response.action_results.append(
                        ActionResult(
                            status="success",
                            message=f"{extended_request.requester_email} has been give temporary access to {specific_change_arn}. "
                            f"Please allow up to 5 minutes for access to be granted.",
                        )
                    )
                elif specific_change.change_type == "create_resource":
                    if specific_change.principal.resource_type == ResourceType.role:
                        response = await apply_create_role_change(
                            extended_request, specific_change, response, user, tenant
                        )
                elif specific_change.change_type == "delete_resource":
                    try:
                        iam_resource_type = specific_change.principal.resource_type
                        iam_resource_name = specific_change.principal.name
                        if iam_resource_type == ResourceType.role:
                            await IAMRole.delete_role(
                                tenant, account_id, iam_resource_name, user
                            )
                            specific_change.status = Status.applied
                        elif iam_resource_type == ResourceType.user:
                            await delete_iam_user(
                                account_id, iam_resource_name, user, tenant
                            )
                            specific_change.status = Status.applied
                        else:
                            response.errors += 1
                            response.action_results.append(
                                ActionResult(
                                status="error",
                                message="Resource deletion not supported",
                            )
                            )
                    except Exception as e:
                        delete_resource_err_msg = (
                            f"Exception deleting AWS IAM {iam_resource_type}"
                        )
                        log_data["message"] = f"{delete_resource_err_msg}: {str(e)}"
                        response.errors += 1
                        response.action_results.append(
                        ActionResult(
                            status="error",
                            message=delete_resource_err_msg,
                        )
                    )
                elif (
                    specific_change.change_type == "resource_policy"
                    or specific_change.change_type == "sts_resource_policy"
                ):
                    response = await apply_resource_policy_change(
                        extended_request,
                        specific_change,
                        response,
                        user,
                        tenant,
                        custom_aws_credentials=custom_aws_credentials,
                    )
                elif (
                    specific_change.change_type == "resource_tag"
                    and not specific_change.principal.principal_arn.startswith(
                        "arn:aws:iam::"
                    )
                ):
                    response = await apply_non_iam_resource_tag_change(
                        extended_request,
                        specific_change,
                        response,
                        user,
                        tenant,
                        specific_change_arn,
                        custom_aws_credentials=custom_aws_credentials,
                    )
                elif (
                    specific_change.change_type == "resource_tag"
                    and managed_policy_arn_regex.search(specific_change_arn)
                ):
                    response = await apply_managed_policy_resource_tag_change(
                        extended_request,
                        specific_change,
                        response,
                        user,
                        tenant,
                        custom_aws_credentials=custom_aws_credentials,
                    )
                elif specific_change.change_type == "managed_policy_resource":
                    response = await apply_managed_policy_resource_change(
                        extended_request,
                        specific_change,
                        response,
                        user,
                        tenant,
                        custom_aws_credentials=custom_aws_credentials,
                    )
                elif specific_change.change_type == "tra_can_assume_role":
                    response = await apply_tra_role_change(
                        extended_request, specific_change, response, user, tenant
                    )
                elif specific_change.change_type == "assume_role_access":
                    response = await apply_role_access_change(
                        extended_request, specific_change, response, user, tenant
                    )
                elif extended_request.principal.principal_arn:
                    # Save current policy by populating "old" policies at the time of application for historical record
                    extended_request = await populate_old_policies(
                        extended_request, user, tenant
                    )
                    await apply_changes_to_role(
                        extended_request,
                        response,
                        user,
                        tenant,
                        specific_change.id,
                        custom_aws_credentials=custom_aws_credentials,
                    )
                    await update_resource_in_dynamo(
                        tenant, extended_request.principal.principal_arn, force_refresh
                    )
                if specific_change.status == Status.applied:
                    if extended_request.ttl:
                        extended_request.expiration_date = (
                            datetime.utcnow() + timedelta(seconds=extended_request.ttl)
                        )
                        extended_request = (
                            await update_extended_request_expiration_date(
                                tenant,
                                user,
                                extended_request,
                                extended_request.expiration_date,
                            )
                        )
                    # Change was successful, update in dynamo
                    specific_change.updated_by = user
                    response = await _update_dynamo_with_change(
                        user,
                        tenant,
                        extended_request,
                        log_data,
                        response,
                        "Successfully updated change in dynamo",
                        "Error updating change in dynamo",
                        visible=False,
                    )
                    if specific_change_arn:
                        await update_resource_in_dynamo(
                            tenant, specific_change_arn, True
                        )
            else:
                raise NoMatchingRequest(
                    "Unable to find a compatible non-applied change with "
                    "that ID in this policy request"
                )

    elif request_changes.command == Command.cancel_change:
        cancel_change_model = CancelChangeModificationModel.parse_obj(request_changes)
        specific_change = await _get_specific_change(
            extended_request.changes, cancel_change_model.change_id
        )
        if specific_change and specific_change.status == Status.not_applied:
            # Update the status
            specific_change.status = Status.cancelled
            specific_change.updated_by = user
            # Update in dynamo
            success_message = "Successfully updated change in dynamo"
            error_message = "Error updating change in dynamo"
            response = await _update_dynamo_with_change(
                user,
                tenant,
                extended_request,
                log_data,
                response,
                success_message,
                error_message,
                visible=False,
            )
        else:
            raise NoMatchingRequest(
                "Unable to find a compatible non-applied change with "
                "that ID in this policy request"
            )

    elif request_changes.command == Command.cancel_request:
        if extended_request.request_status != RequestStatus.pending:
            raise InvalidRequestParameter(
                "Request cannot be cancelled as it's status "
                f"is {extended_request.request_status.value}"
            )
        for change in extended_request.changes.changes:
            if change.status == Status.applied:
                response.errors += 1
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=(
                            "Request cannot be cancelled because at least one change has been applied already. "
                            "Please apply or cancel the other changes."
                        ),
                    )
                )
                response = await maybe_approve_reject_request(
                    extended_request, user, log_data, response, tenant
                )
                return response

        extended_request.request_status = RequestStatus.cancelled
        success_message = "Successfully cancelled request"
        error_message = "Error cancelling request"
        extended_request.reviewer = user
        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            success_message,
            error_message,
        )
        await send_communications_policy_change_request_v2(extended_request, tenant)

    elif request_changes.command == Command.reject_request:
        if extended_request.request_status != RequestStatus.pending:
            raise InvalidRequestParameter(
                f"Request cannot be rejected "
                f"as it's status is {extended_request.request_status.value}"
            )
        for change in extended_request.changes.changes:
            if change.status == Status.applied:
                response.errors += 1
                response.action_results.append(
                    ActionResult(
                        status="error",
                        message=(
                            "Request cannot be rejected because at least one change has been applied already. "
                            "Please apply or cancel the other changes."
                        ),
                    )
                )
                response = await maybe_approve_reject_request(
                    extended_request, user, log_data, response, tenant
                )
                return response

        extended_request.request_status = RequestStatus.rejected
        success_message = "Successfully rejected request"
        error_message = "Error rejected request"
        extended_request.reviewer = user
        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            success_message,
            error_message,
        )
        await send_communications_policy_change_request_v2(extended_request, tenant)

    elif request_changes.command == Command.move_back_to_pending:
        extended_request.request_status = RequestStatus.pending
        success_message = "Successfully moved request back to pending"
        error_message = "Error moving request back to pending"
        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            success_message,
            error_message,
        )

    # This marks a request as complete. This essentially means that all necessary actions have been taken with the
    # request, and doesn't apply any changes.
    elif request_changes.command == Command.approve_request:
        if extended_request.request_status != RequestStatus.pending:
            raise InvalidRequestParameter(
                "Request cannot be approved as it's "
                f"status is {extended_request.request_status.value}"
            )

        # Save current policy by populating "old" policies at the time of application for historical record
        # extended_request = await populate_old_policies(extended_request, user, tenant)
        if extended_request.principal.principal_arn:
            # Save current policy by populating "old" policies at the time of application for historical record
            extended_request = await populate_old_policies(
                extended_request, user, tenant
            )
        extended_request.request_status = RequestStatus.approved
        extended_request.reviewer = user

        success_message = "Successfully updated request status"
        error_message = "Error updating request in dynamo"

        response = await _update_dynamo_with_change(
            user,
            tenant,
            extended_request,
            log_data,
            response,
            success_message,
            error_message,
            visible=False,
        )
        # maybe_approve_reject_request already sends approved requests so no need to send it twice
        if not auto_approved:
            await send_communications_policy_change_request_v2(extended_request, tenant)
        await update_resource_in_dynamo(
            tenant, extended_request.principal.principal_arn, force_refresh
        )

    response = await maybe_approve_reject_request(
        extended_request, user, log_data, response, tenant, auto_approved=auto_approved
    )

    log_data["message"] = "Done parsing/applying request modification changes"
    log_data["request"] = extended_request.dict()
    log_data["response"] = response.dict()
    log_data["error"] = None
    log.debug(log_data)
    return response


async def get_resources_from_policy_change(change: ChangeModel, tenant):
    """Returns a dict of resources affected by a list of policy changes along with
    the actions and other data points that are relevant to them.

    Returned dict format:
    {
        "resource_name": {
            "actions": ["service1:action1", "service2:action2"],
            "arns": ["arn:aws:service1:::resource_name", "arn:aws:service1:::resource_name/*"],
            "account": "1234567890",
            "type": "service1",
            "region": "",
        }
    }
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
    }
    accounts_d: dict = await get_account_id_to_name_mapping(tenant)
    resource_actions: List = []
    if change.change_type not in ["inline_policy"]:
        return []
    policy_document = change.policy.policy_document
    for statement in policy_document.get("Statement", []):
        resources = statement.get("Resource", [])
        resources = resources if isinstance(resources, list) else [resources]
        for resource in resources:
            # We can't yet generate multiple cross-account resource policies
            # based on a partial wildcard in a resource name
            if "*" in resource:
                continue
            if not resource:
                raise Exception(
                    "One or more resources must be specified in the policy."
                )
            try:
                resource_summary = await ResourceSummary.set(
                    tenant, resource, region_required=True
                )
            except Exception as e:
                log.error(
                    {
                        **log_data,
                        "error": str(e),
                        "message": "Unable to parse resource ARN from the policy change",
                        "resource": resource,
                    }
                )
                sentry_sdk.capture_exception()
                continue

            resource_action = {
                "arn": resource,
                "name": resource_summary.name,
                "account_id": resource_summary.account,
                "region": resource_summary.region,
                "resource_type": resource_summary.service,
                "account_name": accounts_d.get(resource_summary.account),
                "actions": get_actions_for_resource(resource, statement),
            }
            resource_actions.append(ResourceModel.parse_obj(resource_action))
    return resource_actions


def get_actions_for_resource(resource_arn: str, statement: Dict) -> List[str]:
    """For the given resource and policy statement, return the actions that are
    for that resource's service.
    """
    results: List[str] = []
    # Get service from resource
    resource_service = parse_arn(resource_arn)["service"]
    # Get relevant actions from policy doc
    actions = statement.get("Action", [])
    actions = actions if isinstance(actions, list) else [actions]
    for action in actions:
        if action == "*":
            results.append(action)
        else:
            if (
                get_service_from_action(action) == resource_service
                or action.lower() in ["sts:assumerole", "sts:tagsession"]
                and resource_service == "iam"
            ):
                if action not in results:
                    results.append(action)

    return results
