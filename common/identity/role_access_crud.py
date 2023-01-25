import datetime
import uuid
from typing import TYPE_CHECKING, Optional, Union

from sqlalchemy import select, update

from common.config.globals import ASYNC_PG_SESSION
from common.exceptions.exceptions import NoMatchingRequest, Unauthorized
from common.pg_core.filters import create_filter_from_url_params
from common.role_access.models import RoleAccess, RoleAccessTypes
from common.tenants.models import Tenant


if TYPE_CHECKING:
    from common.users.models import User
    from common.groups.models import Group
    from common.identity.models import IdentityRole


async def list_role_access(tenant_name: str, **filter_kwargs) -> list[RoleAccess]:
    filter_kwargs.setdefault("order_by", "-created_at")

    # Figure out filters and custom ordering
    async with ASYNC_PG_SESSION() as session:
        tenant_rows = await session.execute(
            select(Tenant).filter(Tenant.name == tenant_name)
        )
        tenant = tenant_rows.scalars().first()
        if tenant is None:
            return []
        stmt = select(RoleAccess).filter(RoleAccess.tenant == tenant)

        # stmt = create_filter_from_url_params(stmt, **filter_kwargs)
        items = await session.execute(stmt)
    return items.scalars().all()


async def query_role_access(tenant_name: str, user: Optional[User], group: Optional[Group], identity_role: Optional[IdentityRole]):
    async with ASYNC_PG_SESSION() as session:
        tenant = Tenant.get_by_name(tenant_name)
        select_stmt = select(RoleAccess).filter(RoleAccess.tenant == tenant)
        if user:
            select_stmt = select_stmt.filter(RoleAccess.user == user)
        if group:
            select_stmt = select_stmt.filter(RoleAccess.group == group)
        if identity_role:
            select_stmt = select_stmt.filter(RoleAccess.identity_role == identity_role)
        items = await session.execute(select_stmt)
        role_access: RoleAccess = items.scalars().unique().all()
        return role_access


async def delete_role_access(tenant_name: str, role_access_id: Union[str, uuid.UUID]):
    async with ASYNC_PG_SESSION() as session:
        tenant = await session.execute(
            select(Tenant).filter(Tenant.name == tenant_name)
        )
        async with session.begin():
            await session.execute(
                update(RoleAccess)
                .where(RoleAccess.id == role_access_id)
                .where(RoleAccess.tenant == tenant)
                .values(deleted=True, deleted_at=datetime.datetime.utcnow())
            )


async def get_role_access(
    tenant: str,
    role_access_id: Optional[Union[str, uuid.UUID]] = None,
    role_arn: Optional[str] = None,
) -> RoleAccess:
    try:
        async with ASYNC_PG_SESSION() as session:
            if role_access_id:
                stmt = (
                    select(RoleAccess)
                    .filter(RoleAccess.id == role_access_id)
                    .filter(RoleAccess.tenant == tenant)
                )
            elif role_arn:
                stmt = (
                    select(RoleAccess)
                    .filter(RoleAccess.identity_role == role_arn)
                    .filter(RoleAccess.tenant == tenant)
                )
            else:
                raise NoMatchingRequest

            items = await session.execute(stmt)
            request: RoleAccess = items.scalars().unique().one()
            return request
    except Exception:
        raise NoMatchingRequest


async def create_role_access(
    tenant: str,
    created_by: str,
    type: RoleAccessTypes,
    user_id: str,
    group_id: str,
    role_arn: str,
    cli_only: bool,
    expiration: datetime,
    request_id: str,
    cloud_provider: str = "aws",
    signature: str = None,
):

    role_access = RoleAccess(
        id=uuid.uuid4(),
        created_by=created_by,
        type=type,
        tenant=tenant,
        user_id=user_id,
        group_id=group_id,
        role_arn=role_arn,
        cli_only=cli_only,
        expiration=expiration,
        request_id=request_id,
        cloud_provider=cloud_provider,
        signature=signature,
    )

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            session.add(role_access)


async def update_role_access(
    tenant: str,
    role_access_id: Union[str, uuid.UUID],
    updated_by: str,
    type: RoleAccessTypes = None,
    user_id: str = None,
    group_id: str = None,
    role_arn: str = None,
    cli_only: bool = None,
    expiration: datetime = None,
    request_id: str = None,
    cloud_provider: str = "aws",
    signature: str = None,
):
    arguments = locals()
    role_access = await get_role_access(tenant, role_access_id)
    if (
        (
            role_access.created_by != updated_by
            and updated_by not in role_access.allowed_approvers
        )
        or role_access.status != "Pending"
        or role_access.deleted
    ):
        raise Unauthorized("Unable to update this role_access")

    updates = [
        arg for arg in arguments if arg and arg != "role_access_id" and arg != "tenant"
    ]

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            await session.execute(
                update(RoleAccess)
                .where(RoleAccess.id == role_access_id)
                .values(*updates)
            )
