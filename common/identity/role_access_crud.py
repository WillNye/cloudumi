import asyncio
import datetime
import uuid
from typing import Union

from sqlalchemy import and_, select, update

from common.config.globals import ASYNC_PG_SESSION
from common.exceptions.exceptions import (
    NoMatchingRequest,
    NoMatchingTenant,
    Unauthorized,
)
from common.identity.models import RoleAccess, RoleAccessTypes, Tenant
from common.pg_core.filters import create_filter_from_url_params


async def list_role_access(tenant: str, **filter_kwargs) -> list[RoleAccess]:
    filter_kwargs.setdefault("order_by", "-created_at")

    # Figure out filters and custom ordering
    async with ASYNC_PG_SESSION() as session:
        stmt = (select(RoleAccess).filter(Tenant.name == tenant)).innerjoin(
            Tenant,
            and_(
                RoleAccess.tenant_id == Tenant.id,
            ),
        )

        stmt = create_filter_from_url_params(stmt, **filter_kwargs)
        items = await session.execute(stmt)
    return items.scalars().all()


async def get_role_access(
    tenant: str, role_access_id: Union[str, uuid.UUID]
) -> RoleAccess:
    try:
        async with ASYNC_PG_SESSION() as session:
            stmt = (
                select(RoleAccess)
                .filter(RoleAccess.id == role_access_id)
                .filter(Tenant.name == tenant)
            ).innerjoin(
                Tenant,
                and_(
                    RoleAccess.tenant_id == Tenant.id,
                ),
            )

            items = await session.execute(stmt)
            request: RoleAccess = items.scalars().unique().one()
            return request
    except Exception:
        raise NoMatchingRequest


async def create_role_access(
    tenant: str,
    created_by: str,
    justification: str,
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
        justification=justification,
        type=type,
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
            tenant = session.execute(select(Tenant).filter(Tenant.name == tenant))
            if not tenant:
                raise NoMatchingTenant(f"Tenant {tenant} does not exist")

            role_access.tenant_id = tenant[0].id
            session.add(role_access)


async def update_role_access(
    tenant: str,
    role_access_id: Union[str, uuid.UUID],
    updated_by: str,
    justification: str = None,
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
            tenant = session.execute(select(Tenant).filter(Tenant.name == tenant))
            if not tenant:
                raise NoMatchingTenant(f"Tenant {tenant} does not exist")
            session.execute(
                update(RoleAccess)
                .where(RoleAccess.id == role_access_id)
                .values(*updates)
            )


asyncio.run(
    create_role_access(
        "test_tenant",
        "created",
        "because",
        RoleAccessTypes.credential_access,
        "user",
        "group",
        "role_arn",
        True,
        datetime.datetime.now(),
        "request",
    )
)
asyncio.run(
    create_role_access(
        "test_tenant",
        "created",
        "because",
        RoleAccessTypes.tra_active_user,
        "user",
        "group",
        "role_arn",
        True,
        datetime.datetime.now(),
        "request",
    )
)
asyncio.run(
    create_role_access(
        "test_tenant",
        "created",
        "because",
        RoleAccessTypes.tra_supported_group,
        "user",
        "group",
        "role_arn",
        True,
        datetime.datetime.now(),
        "request",
    )
)
asyncio.run(list_role_access("test_tenant", order_by="-created_at"))
asyncio.run(get_role_access("test_tenant", "1"))
asyncio.run(
    update_role_access(
        "test_tenant",
        "1",
        "updated",
        "because",
        RoleAccessTypes.tra_supported_group,
        "user",
        "group",
        "role_arn",
        True,
        datetime.datetime.now(),
        "request",
    )
)
