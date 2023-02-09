import os

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from common.config.globals import ASYNC_PG_ENGINE  # noqa: E402
from common.group_memberships.models import GroupMembership  # noqa: E402
from common.groups.models import Group  # noqa: E402
from common.pg_core.models import Base  # noqa: F401,E402
from common.users.models import User  # noqa: E402


async def rebuild_tables():
    async with ASYNC_PG_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with ASYNC_PG_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with ASYNC_PG_ENGINE.begin() as conn:
        user = await User.create(
            "cloudumidev_com",
            "admin_user@noq.dev",
            "admin_user@noq.dev",
            "Password!1",
            email_verified=True,
            managed_by="MANUAL",
        )
        group = await Group.create(
            tenant="cloudumidev_com",
            name="noq_admins",
            email="noq_admins@noq.dev",
            description="test",
        )
        await GroupMembership.create(user, group)


def run_alembic_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
