import os

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from common.config.globals import ASYNC_PG_ENGINE  # noqa: E402
from common.group_memberships.models import GroupMembership  # noqa: E402
from common.groups.models import Group  # noqa: E402
from common.pg_core.models import Base  # noqa: E402
from common.tenants.models import Tenant  # noqa: E402
from common.users.models import User  # noqa: E402


async def rebuild_tables():
    async with ASYNC_PG_ENGINE.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all, checkfirst=False)
        tables = Base.metadata.sorted_tables
        for table in tables:
            await conn.execute(text(f"drop table if exists {table.name} cascade;"))
    async with ASYNC_PG_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with ASYNC_PG_ENGINE.begin() as conn:
        tenant = await Tenant.create(
            name="localhost",
            organization_id="localhost",
        )
        tenant_cloudumidev = await Tenant.create(
            name="cloudumidev_com",
            organization_id="cloudumidev_com",
        )
        user = await User.create(
            tenant,
            "admin_user@noq.dev",
            "admin_user@noq.dev",
            "Password!1",
            email_verified=True,
            managed_by="MANUAL",
        )
        group = await Group.create(
            tenant=tenant,
            name="noq_admins",
            email="noq_admins@noq.dev",
            description="test",
            managed_by="MANUAL",
        )
        await GroupMembership.create(user, group)
        user2 = await User.create(
            tenant_cloudumidev,
            "admin_user@noq.dev",
            "admin_user@noq.dev",
            "Password!1",
            email_verified=True,
        )
        group2 = await Group.create(
            tenant=tenant_cloudumidev,
            name="noq_admins",
            email="noq_admins@noq.dev",
            description="test",
        )
        await GroupMembership.create(user2, group2)


def run_alembic_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
