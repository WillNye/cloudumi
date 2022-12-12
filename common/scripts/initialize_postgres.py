import asyncio
import os

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

from common.config.config import pg_engine  # noqa: F401,E402
from common.pg_core.models import Base  # noqa: F401,E402


async def rebuild_tables():
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(rebuild_tables())
