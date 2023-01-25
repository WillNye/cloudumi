import base64
import hashlib
import secrets
import urllib.parse
import uuid
from datetime import date, datetime, timedelta
from uuid import uuid4

import pyotp
import ujson as json
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship, selectinload
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.group_memberships.models import GroupMembership  # noqa
from common.lib.notifications import send_email_via_sendgrid
from common.pg_core.filters import (
    DEFAULT_SIZE,
    create_filter_from_url_params,
    determine_page_from_offset,
)
from common.pg_core.models import Base, SoftDeleteMixin
from common.templates import (
    generic_email_template,
    new_user_with_password_email_template,
)


class User(SoftDeleteMixin, Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active = Column(Boolean, default=True)
    username = Column(String, nullable=False, index=True)
    email: str = Column(String, nullable=False, index=True)
    email_type: str = Column(String, nullable=True)
    locale: str = Column(String, nullable=True)
    external_id: str = Column(String, nullable=True)
    email_primary: bool = Column(Boolean, default=True)
    email_verified: bool = Column(Boolean, default=False)
    email_verify_token: str = Column(String, nullable=True)
    email_verify_token_expiration: datetime = Column(DateTime, nullable=True)
    # TODO: Force password reset flow after temp password created (Or just send them a
    # password reset)
    password_reset_required: bool = Column(Boolean, default=False)
    password_hash = Column(String, nullable=False)
    password_reset_token = Column(String, nullable=True)
    password_reset_token_expiration = Column(DateTime, nullable=True)
    login_attempts = Column(Integer, default=0)
    login_magic_link_token = Column(String, nullable=True)
    login_magic_link_token_expiration = Column(DateTime, nullable=True)
    display_name = Column(String, nullable=True)
    full_name = Column(String)
    given_name = Column(String)
    middle_name = Column(String)
    family_name = Column(String)
    mfa_secret = Column(String)
    mfa_secret_temp = Column(String)
    mfa_enabled = Column(Boolean, default=False)
    mfa_primary_method = Column(String(64), nullable=True)
    mfa_phone_number = Column(String(128), nullable=True)
    last_successful_mfa_code = Column(String(64), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)

    tenant = relationship("Tenant")

    # TODO: When we're soft-deleting, we need our own methods to get these groups
    # because `deleted=true`. Create async delete function to update the relationship
    # object for users and groups.
    # groups = relationship("GroupMembership", back_populates="user", lazy="subquery")
    groups = relationship(
        "Group",
        secondary=GroupMembership.__table__,
        back_populates="users",
        foreign_keys=[GroupMembership.user_id, GroupMembership.group_id],
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
    )

    async def delete(self):
        # Delete all group memberships
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                group_memberships = await session.execute(
                    select(GroupMembership).where(
                        and_(GroupMembership.user_id == self.id)
                    )
                )
                self.deleted = True
                self.username = f"{self.username}-{self.id}"
                self.email = f"{self.email}-{self.id}"
                await self.write()
        for group_membership in group_memberships.scalars().all():
            await group_membership.delete()
        return True

    # Should be soft deletes because headaches when people leave and we need auditability.
    # users = relationship(
    #     'User',
    #     secondary='group_memberships',
    #     back_populates='groups',
    # )

    async def group_delete(query):
        # Include on query to update the user membership and set deleted to true for those as well
        # deleted=false for group memberships and all groups impacted by that group
        # Set groups as deleted, and memberships to groups as deleted
        pass

    def __repr__(self):
        return (
            f"<{self.__class__.__name__}("
            f"id={self.id}, "
            f"full_name={self.full_name}, "
            f")>"
        )

    @classmethod
    async def generate_password_hash(cls, password):
        """Hash the given password and return the hash."""
        salt = base64.b64encode(uuid.uuid4().bytes).decode("utf-8")
        password_hash = hashlib.sha512((password + salt).encode("utf-8")).hexdigest()
        return f"{salt}${password_hash}"

    async def set_password(self, password):
        """Hash the given password and store it in the password_hash field."""
        self.password_hash = await self.generate_password_hash(password)

    async def user_initiated_password_reset(self, password):
        """Set the user's password and reset the password reset token."""
        await self.set_password(password)
        self.password_reset_token = None
        self.password_reset_token_expiration = None
        self.password_reset_required = False
        await self.write()

    async def check_password(self, password):
        """Check if the given password matches the stored password hash."""
        salt, password_hash = self.password_hash.split("$")
        return (
            password_hash
            == hashlib.sha512((password + salt).encode("utf-8")).hexdigest()
        )

    async def write(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(self)
                await session.commit()
            return True

    async def set_mfa_secret(self, mfa_secret) -> bool:
        """Generate a new MFA secret"""
        self.mfa_secret = mfa_secret
        await self.write()
        return True

    async def set_mfa_secret_temp(self):
        """Generate a new MFA secret"""
        self.mfa_secret_temp = pyotp.random_base32()
        await self.write()
        return self.mfa_secret_temp

    async def enable_mfa(self, token):
        """Enable MFA after the user has verified their MFA token."""
        if await self.check_temp_mfa(token):
            self.mfa_secret = self.mfa_secret_temp
            self.mfa_secret_temp = None
            self.mfa_enabled = True
            await self.write()
            return True
        return False

    async def get_totp_uri(self):
        label = urllib.parse.quote_plus(self.tenant.replace("_", "."))
        mfa_secret_temp = self.mfa_secret_temp
        if not mfa_secret_temp:
            mfa_secret_temp = self.set_mfa_secret_temp()
        return f"otpauth://totp/{label}:{self.email}?secret={mfa_secret_temp}&issuer={label}"

    async def disable_mfa(self):
        """Disable MFA for the user and clear the MFA secret."""
        self.mfa_secret = None
        self.mfa_enabled = False
        await self.write()

    async def check_mfa(self, token):
        """Check if the given MFA token is valid."""
        totp = pyotp.TOTP(self.mfa_secret)
        # Prevent token re-use
        if token == self.last_successful_mfa_code:
            return False
        verified = totp.verify(token)
        if verified:
            self.last_successful_mfa_code = token
            await self.write()

        return verified

    async def check_temp_mfa(self, token):
        """Check if the given MFA token is valid."""
        totp = pyotp.TOTP(self.mfa_secret_temp)
        return totp.verify(token)

    @classmethod
    async def update(cls, id, username, **kwargs):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                user = session.query(User).get(id)
                user.username = username
                session.add(user)
                await session.commit()

    @classmethod
    async def get_by_id(cls, tenant, user_id, get_groups=False):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    and_(
                        User.tenant == tenant,
                        User.id == user_id,
                        User.deleted == False,  # noqa
                    )
                )
                if get_groups:
                    stmt = stmt = stmt.options(selectinload(User.groups))
                user = await session.execute(stmt)
                return user.scalars().first()

    @classmethod
    async def get_by_username(cls, tenant, username, get_groups=False):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    and_(
                        User.tenant == tenant,
                        User.username == username,
                        User.deleted == False,  # noqa
                    )
                )
                if get_groups:
                    stmt = stmt = stmt.options(selectinload(User.groups))
                user = await session.execute(stmt)
                return user.scalars().first()

    @classmethod
    async def get_by_email(cls, tenant, email, get_groups=False):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    and_(
                        User.tenant == tenant,
                        User.email == email,
                        User.deleted == False,  # noqa
                    )
                )
                if get_groups:
                    stmt = stmt = stmt.options(selectinload(User.groups))
                user = await session.execute(stmt)
                return user.scalars().first()

    @classmethod
    async def get_all(
        cls,
        tenant,
        get_groups=False,
        count=DEFAULT_SIZE,
        offset=0,
        page=0,
        filters=None,
    ):
        if not filters:
            filters = {}
        if not page:
            page = determine_page_from_offset(offset, count)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    User.tenant == tenant, User.deleted == False  # noqa
                )
                stmt = create_filter_from_url_params(stmt, page, count, **filters)
                if get_groups:
                    stmt = stmt.options(selectinload(User.groups))
                users = await session.execute(stmt)
                return users.scalars().all()

    @classmethod
    async def create(cls, tenant, username, email, password, **kwargs):
        user = cls(
            id=str(uuid4()),
            tenant=tenant,
            username=username,
            email=email,
            password_reset_required=True,
            **kwargs,
        )
        await user.set_password(password)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(user)
                await session.commit()
        return user

    @classmethod
    async def generate_login_link(cls, user):
        # Generate a random token
        token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")

        user.login_magic_link_token = token
        user.login_magic_link_token_expiration = datetime.utcnow() + timedelta(
            minutes=15
        )

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.update(user)
                await session.commit()
        # Return the token
        return user.login_magic_link_token

    @classmethod
    async def verify_email(cls, tenant, email, token):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    and_(
                        User.tenant == tenant,
                        User.email == email,
                        User.email_verify_token == token,
                        User.email_verify_token_expiration >= datetime.utcnow(),
                        User.deleted == False,  # noqa
                    )
                )
                user = await session.execute(stmt)
                user = user.scalars().first()
                if user:
                    user.email_verified = True
                    user.email_verify_token = None
                    user.email_verify_token_expiration = None
                    session.add(user)
                    await session.commit()
                    return True
                else:
                    return False

    async def send_verification_email(self, tenant_url):
        """Sends an email to the given address with a URL to click on to verify their email.

        Args:
            email (str): The email address to send the verification email to.
            expiration_time (datetime.datetime): The time at which the verification link will expire.
        """
        if self.email_verified or (
            self.email_verify_token_expiration
            and self.email_verify_token_expiration >= datetime.utcnow()
        ):
            return False
        # Generate a unique ID for the verification link
        email_verify_token = str(uuid.uuid4())
        email_verify_blob = {
            "email": self.email,
            "tenant": self.tenant,
            "email_verify_token": email_verify_token,
        }
        email_verify_blob_j = json.dumps(email_verify_blob)

        self.email_verify_token = email_verify_token
        self.email_verify_token_expiration = datetime.utcnow() + timedelta(minutes=15)
        await self.write()

        email_verify_blob_j_url_safe = base64.urlsafe_b64encode(
            email_verify_blob_j.encode("utf-8")
        ).decode("utf-8")

        # Build the verification URL
        verification_url = tenant_url.join(
            f"/api/v4/verify?token={email_verify_blob_j_url_safe}"
        ).url

        body_text = (
            f'Please click on <a href="{verification_url}">this link</a> within the '
            "next 15 minutes to verify your email address "
        )

        password_reset_email = generic_email_template.render(
            year=date.today().year,
            header="Verify your E-mail Address",
            body_text=body_text,
        )

        # Send the email with the verification URL
        await send_email_via_sendgrid(
            to_addresses=[self.email],
            subject="Verify your E-mail Address",
            body=password_reset_email,
        )
        return True

    @classmethod
    async def reset_password(cls, tenant, email, token, password):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    and_(
                        User.tenant == tenant,
                        User.email == email,
                        User.password_reset_token == token,
                        User.password_reset_token_expiration >= datetime.utcnow(),
                        User.deleted == False,  # noqa
                    )
                )
                user = await session.execute(stmt)
                user = user.scalars().first()
                if user:
                    user.password_reset_token = None
                    user.password_reset_token_expiration = None
                    await user.set_password(password)
                    session.add(user)
                    await session.commit()
                    return True
                else:
                    return False

    async def send_password_reset_email(self, tenant_url):
        # There's already a password reset token, and it hasn't expired yet.
        if (
            self.password_reset_token_expiration
            and self.password_reset_token_expiration >= datetime.utcnow()
        ):
            return True
        # Generate a unique ID for the reset link
        password_reset_token = str(uuid.uuid4())
        password_reset_blob = {
            "email": self.email,
            "tenant": self.tenant,
            "password_reset_token": password_reset_token,
        }
        password_reset_blob_j = json.dumps(password_reset_blob)
        self.password_reset_token = password_reset_token
        self.password_reset_token_expiration = datetime.utcnow() + timedelta(minutes=15)
        await self.write()
        password_reset_blob_j_url_safe = base64.urlsafe_b64encode(
            password_reset_blob_j.encode("utf-8")
        ).decode("utf-8")

        # Build the reset URL
        password_reset_url = tenant_url.join(
            f"/login/password-reset?token={password_reset_blob_j_url_safe}"
        ).url

        body_text = (
            "You seem to be trying to reset your password. To complete the process, "
            f'please reset your password through <a href="{password_reset_url}">this link</a> '
            "within the next 15 minutes. If the link expires, you will need to request a new one."
        )
        password_reset_email = generic_email_template.render(
            year=date.today().year,
            header="Password Reset",
            body_text=body_text,
        )

        # Send the email with the reset URL
        await send_email_via_sendgrid(
            to_addresses=[self.email],
            subject="Password Reset Request",
            body=password_reset_email,
        )

    async def send_password_via_email(self, tenant_url, password: str):
        cognito_invitation_message = new_user_with_password_email_template.render(
            year=date.today().year,
            domain=tenant_url.url,
            username=self.email,
            password=password,
        )
        await send_email_via_sendgrid(
            to_addresses=[self.email],
            subject="Your Noq Credentials",
            body=cognito_invitation_message,
        )

    async def verify_password_reset_token(self, token):
        if (
            self.password_reset_token == token
            and self.password_reset_token_expiration >= datetime.utcnow()
        ):
            return True
        else:
            return False

    async def serialize_for_scim(self):
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": self.id,
            "userName": self.username,
            "name": {
                "givenName": self.given_name,
                "middleName": self.middle_name,
                "familyName": self.family_name,
            },
            "emails": [
                {
                    "value": self.email,
                    "primary": self.email_primary,
                    "type": self.email_type,
                }
            ],
            "displayName": self.display_name,
            "locale": self.locale,
            "externalId": self.external_id,
            "active": self.active,
            "groups": [group.name for group in self.groups],
            "meta": {"resourceType": "User"},
        }
