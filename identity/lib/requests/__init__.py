import time
import uuid

from common.lib.dynamo import UserDynamoHandler
from common.lib.slack import send_slack_notification_new_group_request
from identity.lib.groups.groups import add_users_to_groups, get_group_by_name
from identity.lib.groups.models import (
    GroupRequest,
    GroupRequestStatus,
    LastUpdated,
    User,
)


async def get_request_by_id(host, request_id):
    """
    Get a request by ID.
    """
    ddb = UserDynamoHandler(host)
    request_j = await ddb.get_identity_group_request_by_id(host, request_id)
    request = GroupRequest.parse_obj(request_j)
    return request


async def cancel_group_request(host, request, actor, reviewer_comments):
    """
    Approve a request to access a group.
    """
    ddb = UserDynamoHandler(host)
    await ddb.change_request_status_by_id(
        host, request.request_id, "cancelled", actor, reviewer_comments
    )
    # await send_slack_notification_new_group_request(host, request, actor)


async def approve_group_request(host, request, actor, reviewer_comments):
    """
    Approve a request to access a group.
    """
    await add_users_to_groups(host, request.users, request.groups, actor)
    ddb = UserDynamoHandler(host)
    await ddb.change_request_status_by_id(
        host, request.request_id, "approved", actor, reviewer_comments
    )
    # await send_slack_notification_new_group_request(host, request, actor)


async def request_access_to_group(
    host,
    user,
    actor,
    actor_groups,
    idp_name,
    group_name,
    justification,
    group_expiration,
):
    """
    Request access to a group.
    """

    # TODO: Support multiple users being added to multiple groups
    ddb = UserDynamoHandler(host, user)
    errors = []
    user_id = f"{idp_name}-{user}"
    # TODO: get user's groups, and not actor's groups, to determine if user is in the group
    # being requested or not
    # if group_name in user_groups:
    #     errors.append(f"User is already in group: {group_name}")
    #     continue

    # Get the group
    group = await get_group_by_name(host, idp_name, group_name)
    if not group:
        raise Exception("Group not found: {group_name}")

    if not group.attributes.requestable:
        raise Exception(f"Group not requestable: {group_name}")

    # TODO: Check for existing pending requests
    pending_requests = await ddb.get_pending_identity_group_requests(
        host, user=user, group=group, status="pending"
    )
    if pending_requests:
        errors.append(
            f"User already has a pending request for this group: {group_name}"
        )

    user_obj = User(
        idp_name=idp_name,
        user_id=user_id,
        username=user,
        host=host,
        background_check_status=False,
    )
    # Create the request
    request_uuid = str(uuid.uuid4())
    request_status = GroupRequestStatus("pending")
    current_time = int(time.time())
    request_last_updated = LastUpdated(
        user=user_obj, time=current_time, comment="Request Created"
    )

    # TODO: Get user from a function, similar to how we get groups

    # TODO: Check for correct domain

    # TODO: Check background check requirement

    # TODO: Check restricted status on group

    # Approve if no secondary approver

    if (
        not group.attributes.manager_approval_required
        and not group.attributes.approval_chain
    ):
        request_status = GroupRequestStatus("approved")
        request_last_updated.comment = "Request Self-Approved - No Approval Chain"

    # TODO: Approve if user in self-approval groups
    # if group.attributes.self_approval_groups:
    #     for user_group in user_groups:
    #         if user_group in group.attributes.self_approval_groups:
    #             request_status = GroupRequestStatus("approved")
    #             request_last_updated.comment = (
    #                 "Request Self-Approved - User in Self Approval Group"
    #             )
    #             break

    users = [user_obj]
    groups = [group]
    request = GroupRequest(
        request_id=request_uuid,
        host=host,
        users=users,
        groups=groups,
        requester=user_obj,
        justification=justification,
        # TODO: expires=expires,
        status=request_status,
        created_time=current_time,
        last_updated=[request_last_updated],
        last_updated_time=current_time,
        last_updated_by=user_obj,
        request_url=f"/group_request/{request_uuid}",
    )

    # Create request in DynamoDB
    ddb = UserDynamoHandler(host, user=user)
    await ddb.create_identity_group_request(host, user, request)
    # await send_slack_notification_new_group_request(host, request)

    # TODO: Notify approvers via Slack/Email
    # https://github.com/Netflix/consoleme/commit/8b1f020253dc4f90ef2b336a8b75032eab66f241

    # TODO: If status approved, call function to add user to group and notify user
    # TODO: Trigger notification in ConsoleMe
    # TODO: Tell user request was successful and provide context

    return request
