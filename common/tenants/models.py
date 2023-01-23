from sqlalchemy import Column, Integer, String

from common.pg_core.models import Base, SoftDeleteMixin


class Tenant(SoftDeleteMixin, Base):
    __tablename__ = "tenant"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    organization_id = Column(String)
