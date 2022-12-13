from sqlalchemy.ext.asyncio.engine import AsyncEngine, create_async_engine
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

    @property
    def postgres_host(self) -> str:
        return config.get("_global_.secrets.postgres.host", "localhost")

    @property
    def postgres_port(self) -> str:
        return config.get("_global_.secrets.postgres.port", "5432")

    @property
    def postgres_username(self) -> str:
        return config.get("_global_.secrets.postgres.username", "postgres")

    @property
    def postgres_password(self) -> str:
        return config.get("_global_.secrets.postgres.password", "local_dev")

    @property
    def postgres_database(self) -> str:
        return config.get("_global_.secrets.postgres.database", "noq")

    @property
    def postgres_async_sqlalchemy_string(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

    @property
    def postgres_async_engine(self) -> AsyncEngine:
        return create_async_engine(
            self.postgres_async_sqlalchemy_string,
            connect_args={"server_settings": {"jit": "off"}},
        )

    @property
    def postgres_async_session(self) -> AsyncSession:
        return sessionmaker(
            self.postgres_async_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
