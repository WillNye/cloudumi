import datetime
import uuid
from typing import Optional, Union

from sqlalchemy import and_
from sqlalchemy import func as sql_func
from sqlalchemy import select, update
from sqlalchemy.orm import contains_eager

from common import IambicTemplate, IambicTemplateContent
from common.config import config
from common.config.globals import ASYNC_PG_SESSION
from common.exceptions.exceptions import NoMatchingRequest, Unauthorized
from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVER_MAP
from common.iambic.templates.utils import get_template_by_id
from common.iambic_request.models import IambicTemplateChange, Request, RequestComment
from common.iambic_request.utils import (
    generate_updated_iambic_template,
    get_allowed_approvers,
    get_iambic_pr_instance,
)
from common.lib import noq_json as json
from common.models import SelfServiceRequestData, SelfServiceValidateRequestData
from common.pg_core.filters import create_filter_from_url_params
from common.tenants.models import Tenant


async def list_requests(tenant_id: int, **filter_kwargs) -> list[Request]:
    filter_kwargs.setdefault("order_by", "-created_at")

    # Figure out filters and custom ordering
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(Request)
            .filter(Request.deleted == False)  # noqa: E712
            .filter(Request.tenant_id == tenant_id)
        )

        stmt = create_filter_from_url_params(stmt, **filter_kwargs)
        items = await session.execute(stmt)
    return items.scalars().all()


async def get_request_response(
    request: Request, request_pr, include_comments: bool = True
) -> dict:
    pr_details = await request_pr.get_request_details()
    pr_details["justification"] = pr_details.pop("description", "")
    pr_details["status"] = request.status
    pr_details["approved_by"] = request.approved_by
    pr_details["rejected_by"] = request.rejected_by
    pr_details["allowed_approvers"] = request.allowed_approvers
    if include_comments:
        pr_details["comments"] = [comment.dict() for comment in request.comments]
    else:
        pr_details["comments"] = []

    return json.loads(json.dumps(pr_details))


async def get_request(tenant_id: int, request_id: Union[str, uuid.UUID]) -> Request:
    try:
        async with ASYNC_PG_SESSION() as session:
            stmt = (
                select(Request)
                .filter(Request.id == request_id)
                .filter(Request.tenant_id == tenant_id)
                .outerjoin(
                    RequestComment,
                    and_(
                        RequestComment.request_id == Request.id,
                        RequestComment.deleted == False,  # noqa: E712
                    ),
                )
                .options(contains_eager(Request.comments))
            )

            items = await session.execute(stmt)
            request: Request = items.scalars().unique().one()
            return request
    except Exception:
        raise NoMatchingRequest


async def request_dict(tenant: Tenant, request_id: Union[str, uuid.UUID]) -> dict:
    request = await get_request(tenant.id, request_id)
    request_pr = await get_iambic_pr_instance(
        tenant, request.id, request.created_by, request.pull_request_id
    )

    response = await get_request_response(request, request_pr)
    del request_pr
    return response


async def get_template_change_for_request(
    tenant: Tenant, request_data: SelfServiceRequestData
) -> IambicTemplateChange:
    if request_data.template:
        request_data.file_path = request_data.template.file_path

    assert bool(
        bool(request_data.iambic_template_id) ^ bool(request_data.file_path)
    ), "iambic_template_id or file_path must be provided"
    assert bool(
        bool(request_data.changes)
        ^ bool(request_data.template)
        ^ bool(request_data.template_body)
    ), "Must provide either changes or template or template_body in the request"
    if request_data.expires_at:
        assert (
            request_data.changes
        ), "The expires_at field can only be used with changes"

    if not request_data.template and not request_data.iambic_template_id:
        async with ASYNC_PG_SESSION() as session:
            stmt = (
                select(IambicTemplate.id)
                .select_from(IambicTemplate)
                .filter(
                    IambicTemplate.tenant_id == tenant.id,
                    IambicTemplate.file_path == request_data.file_path,
                )
            )

            items = await session.execute(stmt)
            request_data.iambic_template_id = items.scalars().one()
            if not request_data.iambic_template_id:
                raise AssertionError(
                    f"No template found for the given file_path - {request_data.file_path}"
                )

    if request_data.template:
        return IambicTemplateChange(
            file_path=request_data.template.file_path,
            template_body=request_data.template.get_body(exclude_unset=False),
        )
    elif request_data.changes:
        iambic_template = await generate_updated_iambic_template(
            tenant.id, request_data
        )
        return IambicTemplateChange(
            file_path=iambic_template.file_path,
            template_body=iambic_template.get_body(exclude_unset=False),
        )

    elif request_data.template_body:
        db_template = await get_template_by_id(
            tenant.id, request_data.iambic_template_id
        )
        return IambicTemplateChange(
            file_path=db_template.file_path,
            template_body=request_data.template_body,
        )


async def create_request(
    tenant: Tenant,
    created_by: str,
    justification: str,
    changes: list[IambicTemplateChange],
    request_method: str,
    slack_username: Optional[str] = None,
    slack_email: Optional[str] = None,
    duration: Optional[str] = None,
    resource_type: Optional[str] = None,
    request_notes: Optional[str] = None,
    slack_channel_id: Optional[str] = None,
    slack_message_id: Optional[str] = None,
):
    request_id = str(uuid.uuid4())
    request_pr = await get_iambic_pr_instance(tenant, request_id, created_by)

    request_link = (
        f"{config.get_tenant_specific_key('url', tenant.name)}/requests/{request_id}"
    )

    comment = (
        f"| Request | {request_link} |\n"
        f"|-------:|:----------|\n"
        f"| Created by | {created_by} |\n"
        f"| Justification  | {justification} |\n"
    )

    branch_name = await request_pr.create_request(
        comment, changes, request_notes=request_notes
    )

    request = Request(
        id=request_id,
        tenant=tenant,
        pull_request_id=request_pr.pull_request_id,
        pull_request_url=request_pr.pull_request_url,
        repo_name=request_pr.iambic_repo.repo_name,
        created_by=created_by,
        allowed_approvers=(
            await get_allowed_approvers(tenant.name, request_pr, changes)
        ),
        request_method=request_method,
        slack_username=slack_username,
        slack_email=slack_email,
        duration=duration,
        resource_type=resource_type,
        request_notes=request_notes,
        slack_channel_id=slack_channel_id,
        slack_message_id=slack_message_id,
        branch_name=branch_name,
    )
    await request.write()

    response = await get_request_response(request, request_pr, False)
    del request_pr
    return {
        "request": request,
        "friendly_request": response,
    }


async def update_request(
    tenant: Tenant,
    request_id: Union[str, uuid.UUID],
    updated_by: str,
    updater_groups: list[str],
    justification: str = None,
    changes: Union[list[IambicTemplateChange], None] = None,
    request_notes: Optional[str] = None,
):
    request = await get_request(tenant.id, request_id)
    if (
        (
            request.created_by != updated_by
            and not any(
                updater_group in request.allowed_approvers
                for updater_group in updater_groups
            )
        )
        or request.status != "Pending"
        or request.deleted
    ):
        raise Unauthorized("Unable to update this request")

    request_pr = await get_iambic_pr_instance(
        tenant, request.id, request.created_by, request.pull_request_id
    )
    await request_pr.update_request(
        updated_by,
        description=justification,
        template_changes=changes,
        reset_branch=True,
        request_notes=request_notes,
    )

    request.justification = justification
    request.request_notes = request_notes
    request.updated_by = updated_by
    request.updated_at = datetime.datetime.now()
    await request.write()

    await request_pr.load_pr()

    response = await get_request_response(request, request_pr)
    del request_pr
    return {
        "request": request,
        "friendly_request": response,
    }


async def approve_request(
    tenant: Tenant,
    request_id: Union[str, uuid.UUID],
    approved_by: str,
    approver_groups: list[str],
):
    """
    Approve as bot
    Comment `iambic apply`
    Need to add a Running status for applying
    Rollback from Running to Approve if running > 10 minutes
    Set status

    Check on interval after comment
    If merged, trigger iambic template db refresh and set status to `Applied`
    If not check for failure footer, set status to `Failing`
    Failing state should not be able to approve from Noq so now what?
    Leave comment on Noq Request with failure comment
    Consume message
    """
    request = await get_request(tenant.id, request_id)

    if (
        not any(
            approver_group in request.allowed_approvers
            for approver_group in approver_groups
        )
        or request.status != "Pending"
        or request.deleted
    ):
        raise Unauthorized("Unable to approve this request")

    request.status = "Running"
    request_pr = await get_iambic_pr_instance(
        tenant, request_id, request.created_by, request.pull_request_id
    )
    await request_pr.load_pr()

    if request_pr.mergeable:
        await request_pr.approve_request(approved_by)
    elif request_pr.closed_at and not request_pr.merged_at:
        # The PR has already been closed (Rejected) but the status was not updated in the DB
        request.status = "Rejected"
        # TODO: Handle this
        # request.rejected_by = ?
    elif request_pr.merged_at:
        # TODO: Handle this
        # The PR has already been merged but the status was not updated in the DB
        # request.approved_by.append(?)
        pass

    if request.status != "Rejected":
        request.approved_by.append(approved_by)

    await request.write()
    response = await get_request_response(request, request_pr)
    del request_pr
    return response


async def reject_request(
    tenant: Tenant,
    request_id: Union[str, uuid.UUID],
    rejected_by: str,
    rejecter_groups: list[str],
):
    request = await get_request(tenant.id, request_id)
    if (
        (
            request.created_by != rejected_by
            and not any(
                rejecter_group in request.allowed_approvers
                for rejecter_group in rejecter_groups
            )
        )
        or request.status != "Pending"
        or request.deleted
    ):
        raise Unauthorized("Unable to reject this request")

    request_pr = await get_iambic_pr_instance(
        tenant, request_id, request.created_by, request.pull_request_id
    )
    await request_pr.reject_request()

    if request_pr.merged_at:
        # TODO: Handle this
        # The PR has already been merged but the status was not updated in the DB
        pass
    elif request_pr.closed_at and not request_pr.merged_at:
        # The PR has already been closed (Rejected) but the status was not updated in the DB
        request.status = "Rejected"
        # TODO: Handle this
        # request.rejected_by = ?
    else:
        request.status = "Rejected"
        request.rejected_by = rejected_by

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            await session.merge(request)
            await session.flush()
            await session.commit()

    response = await get_request_response(request, request_pr)
    del request_pr
    return response


async def can_perform_comment_operation(
    tenant_id: int,
    request_id: uuid.UUID = None,
    comment_id: uuid.UUID = None,
    user: str = None,
):
    assert request_id or (bool(comment_id) and bool(user))

    async with ASYNC_PG_SESSION() as session:
        if request_id:
            stmt = (
                select(sql_func.count())
                .select_from(Request)
                .filter(Request.tenant_id == tenant_id)
                .filter(Request.id == request_id)
                .filter(Request.deleted == False)  # noqa: E712
            )
        else:
            stmt = (
                select(sql_func.count())
                .select_from(RequestComment)
                .join(Request)
                .filter(Request.tenant_id == tenant_id)
                .filter(Request.deleted == False)  # noqa: E712
                .filter(RequestComment.id == comment_id)
                .filter(RequestComment.created_by == user)
            )

        items = await session.execute(stmt)
        return bool(items.scalar())


async def create_request_comment(
    tenant_id: int, request_id: Union[str, uuid.UUID], created_by: str, body: str
):
    if not (await can_perform_comment_operation(tenant_id, request_id)):
        raise Unauthorized

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            session.add(
                RequestComment(request_id=request_id, created_by=created_by, body=body)
            )


async def update_request_comment(
    tenant_id: int, comment_id: Union[str, uuid.UUID], user: str, body: str
):
    if not (
        await can_perform_comment_operation(tenant_id, comment_id=comment_id, user=user)
    ):
        raise Unauthorized("Unable to update this comment")

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = (
                update(RequestComment)
                .values({"body": body})
                .where(RequestComment.id == comment_id)
            )

            await session.execute(stmt)


async def delete_request_comment(
    tenant_id: int, comment_id: Union[str, uuid.UUID], user: str
):
    if not (
        await can_perform_comment_operation(tenant_id, comment_id=comment_id, user=user)
    ):
        raise Unauthorized("Unable to delete this comment")

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = (
                update(RequestComment)
                .values({"deleted": True})
                .where(RequestComment.id == comment_id)
            )

            await session.execute(stmt)


async def run_request_validation(
    tenant: Tenant, request_data: SelfServiceRequestData
) -> SelfServiceValidateRequestData:
    template_change = await get_template_change_for_request(tenant, request_data)
    current_template_body = None
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(IambicTemplate)
            .filter(
                IambicTemplate.tenant_id == tenant.id,
                IambicTemplate.file_path == template_change.file_path,
            )
            .join(
                IambicTemplateContent,
                IambicTemplateContent.iambic_template_id == IambicTemplate.id,
            )
            .options(contains_eager(IambicTemplate.content))
        )
        items = await session.execute(stmt)
        if db_iambic_template := items.scalars().one_or_none():
            provider_ref = TRUSTED_PROVIDER_RESOLVER_MAP[db_iambic_template.provider]
            template_cls = provider_ref.template_map[db_iambic_template.template_type]
            current_template_obj = template_cls(
                file_path=db_iambic_template.file_path,
                **db_iambic_template.content.content,
            )
            current_template_body = current_template_obj.get_body(exclude_unset=False)

    request_data.changes = None
    request_data.expires_at = None
    request_data.template_body = template_change.template_body

    return SelfServiceValidateRequestData(
        current_template_body=current_template_body, request_data=request_data
    )
