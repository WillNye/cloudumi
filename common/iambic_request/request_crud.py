import uuid
from typing import Union

from sqlalchemy import and_
from sqlalchemy import func as sql_func
from sqlalchemy import select, update
from sqlalchemy.orm import contains_eager

from common.config.globals import ASYNC_PG_SESSION
from common.exceptions.exceptions import NoMatchingRequest, Unauthorized
from common.iambic_request.models import IambicTemplateChange, Request, RequestComment
from common.iambic_request.utils import get_allowed_approvers, get_iambic_pr_instance
from common.lib import noq_json as json
from common.pg_core.filters import create_filter_from_url_params


async def list_requests(tenant: str, **filter_kwargs) -> list[Request]:
    filter_kwargs.setdefault("order_by", "-created_at")

    # Figure out filters and custom ordering
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(Request)
            .filter(Request.deleted == False)  # noqa: E712
            .filter(Request.tenant == tenant)
        )

        stmt = create_filter_from_url_params(stmt, **filter_kwargs)
        items = await session.execute(stmt)
    return items.scalars().all()


async def get_request_response(
    request: Request, request_pr, include_comments: bool = True
) -> dict:
    pr_details = await request_pr.get_request_details()
    pr_details["status"] = request.status
    pr_details["approved_by"] = request.approved_by
    pr_details["rejected_by"] = request.rejected_by
    pr_details["allowed_approvers"] = request.allowed_approvers
    if include_comments:
        pr_details["comments"] = [comment.dict() for comment in request.comments]
    else:
        pr_details["comments"] = []

    return json.loads(json.dumps(pr_details))


async def get_request(tenant: str, request_id: Union[str, uuid.UUID]) -> Request:
    try:
        async with ASYNC_PG_SESSION() as session:
            stmt = (
                select(Request)
                .filter(Request.id == request_id)
                .filter(Request.tenant == tenant)
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


async def request_dict(tenant: str, request_id: Union[str, uuid.UUID]) -> dict:
    request = await get_request(tenant, request_id)
    request_pr = await get_iambic_pr_instance(
        tenant, request.id, request.created_by, request.pull_request_id
    )

    response = await get_request_response(request, request_pr)
    del request_pr
    return response


async def create_request(
    tenant: str,
    created_by: str,
    justification: str,
    changes: list[IambicTemplateChange],
):
    request_id = uuid.uuid4()
    request_pr = await get_iambic_pr_instance(tenant, request_id, created_by)
    await request_pr.create_request(justification, changes)

    request = Request(
        id=request_id,
        tenant=tenant,
        pull_request_id=request_pr.pull_request_id,
        repo_name=request_pr.repo_name,
        created_by=created_by,
        allowed_approvers=(await get_allowed_approvers(tenant, request_pr, changes)),
    )

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            session.add(request)

    response = await get_request_response(request, request_pr, False)
    del request_pr
    return response


async def update_request(
    tenant: str,
    request_id: Union[str, uuid.UUID],
    updated_by: str,
    updater_groups: list[str],
    justification: str = None,
    changes: Union[list[IambicTemplateChange], None] = None,
):
    request = await get_request(tenant, request_id)
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
        updated_by, description=justification, template_changes=changes
    )

    await request_pr.load_pr()

    response = await get_request_response(request, request_pr)
    del request_pr
    return response


async def approve_request(
    tenant: str,
    request_id: Union[str, uuid.UUID],
    approved_by: str,
    approver_groups: list[str],
):
    request = await get_request(tenant, request_id)
    if (
        not any(
            approver_group in request.allowed_approvers
            for approver_group in approver_groups
        )
        or request.status != "Pending"
        or request.deleted
    ):
        raise Unauthorized("Unable to approve this request")

    request.status = "Approved"

    request_pr = await get_iambic_pr_instance(
        tenant, request_id, request.created_by, request.pull_request_id
    )
    await request_pr.load_pr()

    if request_pr.mergeable and request_pr.merge_on_approval:
        await request_pr.merge_request()
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
    else:
        request.approved_by.append(approved_by)

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            await session.merge(request)
            await session.flush()
            await session.commit()

    response = await get_request_response(request, request_pr)
    del request_pr
    return response


async def reject_request(
    tenant: str,
    request_id: Union[str, uuid.UUID],
    rejected_by: str,
    rejecter_groups: list[str],
):
    request = await get_request(tenant, request_id)
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
    tenant: str,
    request_id: uuid.UUID = None,
    comment_id: uuid.UUID = None,
    user: str = None,
):
    assert request_id or (bool(comment_id) and bool(user))

    async with ASYNC_PG_SESSION() as session:
        if request_id:
            stmt = (
                select([sql_func.count()])
                .select_from(Request)
                .filter(Request.tenant == tenant)
                .filter(Request.id == request_id)
                .filter(Request.deleted == False)  # noqa: E712
            )
        else:
            stmt = (
                select([sql_func.count()])
                .select_from(RequestComment)
                .join(Request)
                .filter(Request.tenant == tenant)
                .filter(Request.deleted == False)  # noqa: E712
                .filter(RequestComment.id == comment_id)
                .filter(RequestComment.created_by == user)
            )

        items = await session.execute(stmt)
        return bool(items.scalar())


async def create_request_comment(
    tenant: str, request_id: Union[str, uuid.UUID], created_by: str, body: str
):
    if not (await can_perform_comment_operation(tenant, request_id)):
        raise Unauthorized

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            session.add(
                RequestComment(request_id=request_id, created_by=created_by, body=body)
            )


async def update_request_comment(
    tenant: str, comment_id: Union[str, uuid.UUID], user: str, body: str
):
    if not (
        await can_perform_comment_operation(tenant, comment_id=comment_id, user=user)
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
    tenant: str, comment_id: Union[str, uuid.UUID], user: str
):
    if not (
        await can_perform_comment_operation(tenant, comment_id=comment_id, user=user)
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
