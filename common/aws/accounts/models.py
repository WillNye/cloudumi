from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from common.pg_core.models import Base, SoftDeleteMixin


class AWSAccount(SoftDeleteMixin, Base):
    __tablename__ = "aws_account"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String)
    number = Column(String, index=True)
    tenant_id = ForeignKey("tenant.id")

    tenant = relationship("Tenant", back_populates="aws_account", order_by=number)
