import uuid
from typing import Union

from sqlalchemy import and_
from sqlalchemy import func as sql_func
from sqlalchemy import select, update
from sqlalchemy.orm import contains_eager

from common.config.config import async_session
from common.iambic_request.models import Request, RequestComment
from common.iambic_request.utils import get_iambic_pr_instance
from common.pg_core.filters import create_filter_from_url_params


async def list_requests(tenant: str, **filter_kwargs) -> list[Request]:
    filter_kwargs.setdefault("order_by", "-created_at")

    # Figure out filters and custom ordering
    async with async_session() as session:
        stmt = (
            select(Request)
            .filter(Request.deleted == False)
            .filter(Request.tenant == tenant)
        )

        stmt = create_filter_from_url_params(stmt, **filter_kwargs)
        items = await session.execute(stmt)
    return list(items.scalars().all())


async def get_request_response(request: Request, request_pr) -> dict:
    pr_details = await request_pr.get_request_details()
    pr_details["status"] = request.status
    pr_details["approved_by"] = request.approved_by
    pr_details["allowed_approvers"] = request.allowed_approvers
    pr_details["allowed_approvers"] = request.allowed_approvers
    pr_details["comments"] = [comment.dict() for comment in request.comments]

    return pr_details


async def get_request(tenant: str, request_id: Union[str, uuid.UUID]) -> Request:
    async with async_session() as session:
        stmt = (
            select(Request)
            .filter(Request.id == request_id)
            .filter(Request.tenant == tenant)
            .outerjoin(
                RequestComment,
                and_(
                    RequestComment.request_id == Request.id,
                    RequestComment.deleted == False,
                ),
            )
            .options(contains_eager(Request.comments))
        )

        items = await session.execute(stmt)
        request: Request = items.scalars().unique().one()
        return request


async def request_dict(tenant: str, request_id: Union[str, uuid.UUID]) -> dict:
    request = await get_request(tenant, request_id)
    request_pr = await get_iambic_pr_instance(
        tenant, request.id, request.created_by, request.pull_request_id
    )
    return await get_request_response(request, request_pr)


async def create_request(
    tenant: str,
    created_by: str,
    justification: str,
    changes: list,
    allowed_approvers: list,
):
    request_id = uuid.uuid4()
    request_pr = await get_iambic_pr_instance(tenant, request_id, created_by)
    await request_pr.create_request(justification, changes)

    iambic_request = Request(
        id=request_id,
        tenant=tenant,
        pull_request_id=request_pr.pull_request_id,
        repo_name=request_pr.repo_name,
        created_by=created_by,
        allowed_approvers=allowed_approvers,
    )

    async with async_session() as session:
        async with session.begin():
            session.add(iambic_request)

    return await get_request_response(iambic_request, request_pr)


async def update_request(
    tenant: str,
    request_id: Union[str, uuid.UUID],
    updated_by: str,
    justification: str = None,
    changes: list = None,
):
    request = await get_request(tenant, request_id)
    if (
        (
            request.created_by != updated_by
            and updated_by not in request.allowed_approvers
        )
        or request.status != "Pending"
        or request.deleted
    ):
        # Some type of validation error
        raise

    request_pr = await get_iambic_pr_instance(
        tenant, request.id, request.created_by, request.pull_request_id
    )
    await request_pr.update_request(
        updated_by, description=justification, template_changes=changes
    )

    await request_pr.load_pr()
    return await get_request_response(request, request_pr)


async def approve_request(
    tenant: str, request_id: Union[str, uuid.UUID], approved_by: str
):
    request = await get_request(tenant, request_id)
    if (
        approved_by not in request.allowed_approvers
        or request.status != "Pending"
        or request.deleted
    ):
        # Some type of validation error
        raise

    request.status = "Approved"

    request_pr = await get_iambic_pr_instance(
        tenant, request_id, request.created_by, request.pull_request_id
    )

    if request_pr.mergeable and request_pr.merge_on_approval:
        await request_pr.merge_request()
    elif request_pr.closed_at and not request_pr.merged_at:
        # The PR has already been closed (Rejected) but the status was not updated in the DB
        request.status = "Rejected"
        # TODO: Handle this
        # request.rejected_by = ?
    elif request_pr.merged_at:
        # The PR has already been merged but the status was not updated in the DB
        # request.approved_by.append(?)
        pass
    else:
        request.approved_by.append(approved_by)

    async with async_session() as session:
        async with session.begin():
            await session.merge(request)
            await session.flush()
            await session.commit()

    return await get_request_response(request, request_pr)


async def reject_request(
    tenant: str, request_id: Union[str, uuid.UUID], rejected_by: str
):
    request = await get_request(tenant, request_id)
    if (
        (
            request.created_by != rejected_by
            and rejected_by not in request.allowed_approvers
        )
        or request.status != "Pending"
        or request.deleted
    ):
        # Some type of validation error
        raise

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

    async with async_session() as session:
        async with session.begin():
            await session.merge(request)
            await session.flush()
            await session.commit()

    return await get_request_response(request, request_pr)


async def can_perform_comment_operation(
    tenant: str,
    request_id: uuid.UUID = None,
    comment_id: uuid.UUID = None,
    user: str = None,
):
    assert request_id or (bool(comment_id) and bool(user))

    async with async_session() as session:
        if request_id:
            stmt = (
                select([sql_func.count()])
                .select_from(Request)
                .filter(Request.tenant == tenant)
                .filter(Request.id == request_id)
                .filter(Request.deleted == False)
            )
        else:
            stmt = (
                select([sql_func.count()])
                .select_from(RequestComment)
                .join(Request)
                .filter(Request.tenant == tenant)
                .filter(Request.deleted == False)
                .filter(RequestComment.id == comment_id)
                .filter(RequestComment.created_by == user)
            )

        items = await session.execute(stmt)
        return bool(items.scalar())


async def create_request_comment(
    tenant: str, request_id: Union[str, uuid.UUID], created_by: str, body: str
):
    if not (await can_perform_comment_operation(tenant, request_id)):
        # Some meaningful error
        raise

    async with async_session() as session:
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
        # Some meaningful error
        raise

    async with async_session() as session:
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
        # Some meaningful error
        raise

    async with async_session() as session:
        async with session.begin():
            stmt = (
                update(RequestComment)
                .values({"deleted": True})
                .where(RequestComment.id == comment_id)
            )

            await session.execute(stmt)
