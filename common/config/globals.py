from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm.session import sessionmaker

from common.config import config

REDACTED_STR = "********"


class ClusterConfig:
    @property
    def dynamo_retry_count(self) -> int:
        return config.get("_global_.dynamo.retry_count", 10)

    @property
    def dynamo_wait_time_between_retries(self) -> int:
        return config.get("_global_.dynamo.wait_time_between_retries", 5)


ASYNC_PG_CONN_STR = f"postgresql+asyncpg://{config.get('_global_.secrets.postgres.username')}:{config.get('_global_.secrets.postgres.password')}@{config.get('_global_.noq_db.endpoint')}:{config.get('_global_.noq_db.port')}/{config.get('_global_.noq_db.database')}"
ASYNC_PG_ENGINE = create_async_engine(
    ASYNC_PG_CONN_STR, connect_args={"server_settings": {"jit": "off"}}
)
ASYNC_PG_SESSION = sessionmaker(
    ASYNC_PG_ENGINE,
    expire_on_commit=False,
    class_=AsyncSession,
)
