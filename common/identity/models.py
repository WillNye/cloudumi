from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship

from common.pg_core.models import Base, SoftDeleteMixin


class IdentityRole(SoftDeleteMixin, Base):
    __tablename__ = "identity_role"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    role_name = Column(String)
    role_arn = Column(String, index=True)

    tenant = relationship("Tenant", primaryjoin="Tenant.id == IdentityRole.tenant_id")
