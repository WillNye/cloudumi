import os

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from common.config.globals import ClusterConfig  # noqa: E402
from common.pg_core.models import Base  # noqa: F401,E402


async def rebuild_tables():
    async with ClusterConfig().postgres_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def run_alembic_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
