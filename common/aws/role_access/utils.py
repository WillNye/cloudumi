from cachetools import TTLCache
from sqlalchemy import or_, select

from common import AWSRoleAccess, Group, Tenant, User
from common.config.globals import ASYNC_PG_SESSION
from common.core.async_cached import noq_cached
from common.identity.models import AwsIdentityRole


@noq_cached(cache=TTLCache(maxsize=1024, ttl=120), cache_none=False)
async def get_user_eligible_roles(
    tenant: Tenant,
    user: User,
    groups: list[str],
):
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(AwsIdentityRole.role_arn)
            .select_from(AwsIdentityRole)
            .outerjoin(
                AWSRoleAccess, AWSRoleAccess.identity_role_id == AwsIdentityRole.id
            )
            .outerjoin(User, AWSRoleAccess.user_id == User.id)
            .outerjoin(Group, AWSRoleAccess.group_id == Group.id)
            .filter(
                AwsIdentityRole.tenant_id == tenant.id,
                or_(User.id == user.id, Group.name.in_(groups)),
            )
            .order_by(AwsIdentityRole.role_arn)
        )
        items = await session.execute(stmt)
    return items.scalars().unique().all()
