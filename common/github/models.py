from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, String, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select
from sqlalchemy.sql.schema import ForeignKey

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base


class GitHubInstall(Base):
    __tablename__ = "github_installs"

    id = Column(Integer(), primary_key=True, autoincrement=True, unique=True)
    # Note: when usage increase, check if tenant_id looks up deserve an index
    tenant_id = Column(Integer(), ForeignKey("tenant.id"), nullable=False, unique=True)
    tenant = relationship(
        "Tenant",
        primaryjoin="Tenant.id == GitHubInstall.tenant_id",
        back_populates="github_installs",
    )
    # installation_id is defined by Github and typed as integer
    # Note: when usage increase, check if installation_id looks up deserve an index
    installation_id = Column(Integer(), nullable=False)

    @classmethod
    async def create(cls, tenant, installation_id):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                existing_entry = await cls.get(tenant, session=session)
                if existing_entry:
                    existing_entry.installation_id = installation_id
                    entry = existing_entry
                    session.add(entry)
                else:
                    entry = cls(tenant_id=tenant.id, installation_id=installation_id)
                    session.add(entry)
                await session.commit()
        return entry

    async def delete(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.delete(self)
                await session.commit()
        return True

    @classmethod
    async def get(cls, tenant, session=None):
        async def _query(session):
            stmt = select(GitHubInstall).where(
                GitHubInstall.tenant_id == tenant.id,
            )
            result = await session.execute(stmt)
            return result.scalars().first()

        if session:
            return await _query(session)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                return await _query(session)

    @classmethod
    async def get_with_installation_id(cls, installation_id, session=None):
        """Note: You should only called this if you get the installation_id from a verified
        caller like GitHub Webhook events that the payload is signed with valid signature
        """

        async def _query(session):
            stmt = select(GitHubInstall).where(
                GitHubInstall.installation_id == installation_id,
            )
            result = await session.execute(stmt)
            return result.scalars().all()

        if session:
            return await _query(session)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                return await _query(session)


class GitHubOAuthState(Base):
    __tablename__ = "github_oauth_states"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer(), ForeignKey("tenant.id"), nullable=False, unique=True)
    state = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    tenant = relationship(
        "Tenant",
        primaryjoin="Tenant.id == GitHubOAuthState.tenant_id",
        back_populates="github_oauth_states",
    )

    def __init__(self, tenant, state):
        self.tenant = tenant
        self.state = state
        self.expires_at = datetime.utcnow() + timedelta(minutes=10)

    @classmethod
    async def create(cls, tenant, state):
        entry = cls(tenant=tenant, state=state)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                existing_entry = await cls.get_by_tenant(tenant, session=session)
                if existing_entry:
                    existing_entry.state = state
                    existing_entry.expires_at = entry.expires_at
                    entry = existing_entry
                else:
                    session.add(entry)
                await session.commit()
        return entry

    async def delete(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.delete(self)
                await session.commit()
        return True

    @classmethod
    async def get_by_tenant(cls, tenant, session=None):
        async def _query(session):
            stmt = select(GitHubOAuthState).where(
                GitHubOAuthState.tenant_id == tenant.id,
            )
            result = await session.execute(stmt)
            return result.scalars().first()

        if session:
            return await _query(session)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                return await _query(session)

    @classmethod
    async def get(cls, tenant, state, session=None):
        async def _query(session):
            stmt = select(GitHubOAuthState).where(
                and_(
                    GitHubOAuthState.tenant_id == tenant.id,
                    GitHubOAuthState.state == state,  # noqa
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

        if session:
            return await _query(session)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                return await _query(session)

    @classmethod
    async def get_by_state(cls, state, session=None):
        async def _query(session):
            stmt = select(GitHubOAuthState).where(
                and_(
                    GitHubOAuthState.state == state,  # noqa
                )
            )
            tenant = await session.execute(stmt)
            return tenant.scalars().first()

        if session:
            return await _query(session)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                return await _query(session)
