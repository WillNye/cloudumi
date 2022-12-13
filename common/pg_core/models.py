from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import declarative_base

from common.config.globals import ClusterConfig

Base = declarative_base()


class SoftDeleteMixin:
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted = Column(Boolean, default=False)


async def create_all(self):
    async with self._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class AsyncDatabaseSession:
    def __init__(self):
        self._engine = ClusterConfig().postgres_async_engine
        self._session = ClusterConfig().postgres_async_session()

    def __getattr__(self, name):
        return getattr(self._session, name)

    async def create_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


db = AsyncDatabaseSession()
