from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import declarative_base

from common.config.globals import ASYNC_PG_SESSION

DECLARATIVE_BASE = declarative_base()


class Base(DECLARATIVE_BASE):
    __abstract__ = True

    def dict(self):
        raise NotImplementedError

    async def write(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(self)
                await session.commit()
            return True


class SoftDeleteMixin:
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
