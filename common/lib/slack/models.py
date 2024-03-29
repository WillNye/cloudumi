from operator import and_

from slack_bolt.authorization import AuthorizeResult
from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, desc
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from common.config import config
from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant  # noqa: F401,E402

INSTALLATIONS_TABLE = SQLAlchemyInstallationStore.build_installations_table(
    metadata=Base.metadata,
    table_name=SQLAlchemyInstallationStore.default_installations_table_name,
)

BOTS_TABLE = SQLAlchemyInstallationStore.build_bots_table(
    metadata=Base.metadata,
    table_name=SQLAlchemyInstallationStore.default_bots_table_name,
)

OAUTH_STATES_TABLE = SQLAlchemyOAuthStateStore.build_oauth_states_table(
    metadata=Base.metadata,
    table_name=SQLAlchemyOAuthStateStore.default_table_name,
)

log = config.get_logger(__name__)


class SlackBot(Base):
    __tablename__ = "slack_bots"
    __table__ = BOTS_TABLE


async def get_slack_bot(team_id, app_id):
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = (
                select(SlackBot)
                .where(
                    and_(
                        SlackBot.team_id == team_id,
                        SlackBot.app_id == app_id,
                    )
                )
                .order_by(desc(SlackBot.id))
            )
            bot = await session.execute(stmt)
            return bot.scalars().first()


async def get_slack_bot_from_team_id(team_id):
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = (
                select(SlackBot)
                .where(
                    SlackBot.team_id == team_id,
                )
                .order_by(desc(SlackBot.id))
            )
            bot = await session.execute(stmt)
            return bot.scalars().first()


async def get_slack_bot_authorization(enterprise_id, team_id, logger):
    # TODO: Cache the authorization
    slack_bot = await get_slack_bot_from_team_id(team_id)
    # enterprise_id doesn't exist for some teams
    is_valid_enterprise = (
        True
        if ((not slack_bot.enterprise_id) or (enterprise_id == slack_bot.enterprise_id))
        else False
    )
    if (is_valid_enterprise is True) and (slack_bot.team_id == team_id):
        # Return an instance of AuthorizeResult
        # If you don't store bot_id and bot_user_id, could also call `from_auth_test_response` with your bot_token to automatically fetch them
        return AuthorizeResult(
            enterprise_id=enterprise_id,
            team_id=team_id,
            bot_token=slack_bot.bot_token,
            bot_id=slack_bot.bot_id,
            bot_user_id=slack_bot.bot_user_id,
        )

    logger.error("No authorization information was found")


async def get_tenant_from_team_id(team_id):

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = (
                select(Tenant)
                .select_from(SlackTenantInstallRelationship)
                .join(
                    SlackBot,
                    SlackTenantInstallRelationship.slack_bots_id == SlackBot.id,
                )
                .join(Tenant, SlackTenantInstallRelationship.tenant_id == Tenant.id)
                .where(SlackBot.team_id == team_id)
            )
            result = await session.execute(stmt)
            return result.scalars().first()


class TenantOauthRelationship(Base, SoftDeleteMixin):
    __tablename__ = "slack_tenant_oauth_relationships"
    id = Column(Integer(), primary_key=True, autoincrement=True)
    oauth_id = Column(String, nullable=False)
    tenant_id = Column(ForeignKey("tenant.id"))

    tenant = relationship(
        "Tenant", primaryjoin="Tenant.id == TenantOauthRelationship.tenant_id"
    )

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_slack_tenant"),)

    @classmethod
    async def create(cls, tenant, oauth_id):
        entry = cls(tenant_id=tenant.id, oauth_id=oauth_id)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
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
    async def get_by_tenant(cls, tenant):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(TenantOauthRelationship).where(
                    TenantOauthRelationship.tenant_id == tenant.id,
                )
                entry = await session.execute(stmt)
                return entry.scalars().first()

    @classmethod
    async def get_by_oauth_id(cls, oauth_id):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(TenantOauthRelationship).where(
                    TenantOauthRelationship.oauth_id == oauth_id,
                )
                entry = await session.execute(stmt)
                return entry.scalars().first()


class SlackTenantInstallRelationship(Base, SoftDeleteMixin):
    __tablename__ = "slack_tenant_install_relationships"
    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(ForeignKey("tenant.id"))
    slack_bots_id = Column(ForeignKey("slack_bots.id"))

    tenant = relationship(
        "Tenant", primaryjoin="Tenant.id == SlackTenantInstallRelationship.tenant_id"
    )

    slack_bot = relationship("SlackBot", foreign_keys=[slack_bots_id])

    @classmethod
    async def create(cls, tenant, slack_bot_id):
        entry = cls(tenant_id=tenant.id, slack_bots_id=slack_bot_id)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
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
    async def get_by_tenant(cls, tenant):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(SlackTenantInstallRelationship).where(
                    SlackTenantInstallRelationship.tenant_id == tenant.id,
                )
                entry = await session.execute(stmt)
                return entry.scalars().first()
