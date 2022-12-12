from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SoftDeleteMixin:
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted = Column(Boolean, default=False)
    deleted_by = Column(String, nullable=True)
    deleted_at = Column(DateTime, default=datetime.utcnow, nullable=True)
