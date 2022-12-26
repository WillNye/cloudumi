import base64
import hashlib
import secrets
import urllib.parse
import uuid
from datetime import datetime, timedelta
from uuid import uuid4

import pyotp
import ujson as json
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    and_,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.group_memberships.models import GroupMembership  # noqa
from common.lib.notifications import send_email_via_sendgrid
from common.pg_core.models import AsaList, Base


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    email: str = Column(String, nullable=False)
    email_verified: bool = Column(Boolean, default=False)
    email_verify_token: str = Column(String, nullable=True)
    email_verify_token_expiration: datetime = Column(DateTime, nullable=True)
    active: bool = Column(Boolean(), nullable=False, default=True)
    password_hash = Column(String, nullable=False)
    password_reset_token = Column(String, nullable=True)
    password_reset_token_expiration = Column(DateTime, nullable=True)
    login_attempts = Column(Integer, default=0)
    login_magic_link_token = Column(String, nullable=True)

    full_name = Column(String)
    created_at = Column(DateTime, index=True, default=datetime.utcnow)
    created_by = Column(String)
    updated_at = Column(DateTime, index=True, default=datetime.utcnow)
    mfa_secret = Column(String)
    mfa_enabled = Column(Boolean, default=False)
    mfa_primary_method = Column(String(64), nullable=True)
    mfa_phone_number = Column(String(128), nullable=True)
    last_successful_mfa_code = Column(String(64), nullable=True)
    # MFA - one time recovery codes - comma separated.
    mfa_recovery_codes = Column(MutableList.as_mutable(AsaList()), nullable=True)
    tenant = Column(String, nullable=False)
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(64))
    current_login_ip = Column(String(64))
    login_count = Column(Integer)
    groups = relationship(
        "GroupMembership",
        back_populates="user",
    )
    __table_args__ = (
        UniqueConstraint("tenant", "username", name="uq_tenant_username"),
        UniqueConstraint("tenant", "email", name="uq_tenant_email"),
    )

    def __repr__(self):
        return (
            f"<{self.__class__.__name__}("
            f"id={self.id}, "
            f"full_name={self.full_name}, "
            f")>"
        )

    async def set_password(self, password):
        """Hash the given password and store it in the password_hash field."""
        salt = base64.b64encode(uuid.uuid4().bytes).decode("utf-8")
        password_hash = hashlib.sha512((password + salt).encode("utf-8")).hexdigest()
        self.password_hash = f"{salt}${password_hash}"

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

    async def set_mfa_secret(self):
        """Generate a new MFA secret"""
        self.mfa_secret = self.mfa_secret = pyotp.random_base32()
        await self.write()
        return self.mfa_secret

    async def enable_mfa(self, token):
        """Enable MFA after the user has verified their MFA token."""
        if await self.check_mfa(token):
            self.mfa_enabled = True
            await self.write()
            return True
        return False

    async def get_totp_uri(self):
        label = urllib.parse.quote_plus(self.tenant.replace("_", "."))
        mfa_secret = self.mfa_secret
        if not mfa_secret:
            mfa_secret = self.set_mfa_secret()
        return f"otpauth://totp/{label}:{self.email}?secret={mfa_secret}&issuer={label}"

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

    @classmethod
    async def update(cls, id, username, **kwargs):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                user = session.query(User).get(id)
                user.username = username
                session.add(user)
                await session.commit()

    @classmethod
    async def get_by_username(cls, tenant, username):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    and_(User.tenant == tenant, User.username == username)
                )
                user = await session.execute(stmt)
                return user.scalars().first()

    @classmethod
    async def get_by_email(cls, tenant, email):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(
                    and_(User.tenant == tenant, User.email == email)
                )
                user = await session.execute(stmt)
                return user.scalars().first()

    @classmethod
    async def get_all(cls, tenant):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(User).where(User.tenant == tenant)
                users = await session.execute(stmt)
                return users.scalars().all()

    @classmethod
    async def delete(cls, id):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                user = session.query(User).get(id)
                await session.delete(user)
                await session.commit()
        return True

    @classmethod
    async def create(cls, tenant, username, email, password):
        user = cls(id=str(uuid4()), tenant=tenant, username=username, email=email)
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

        # Send the email with the verification URL
        # TODO: Create an actual e-mail template
        await send_email_via_sendgrid(
            to_addresses=[self.email],
            subject="Verify your e-mail address with Noq",
            body=f"""
            Please click on the following link to verify your email address within the next
            15 minutes: {verification_url}
            """,
        )

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
            f"/api/v4/users/forgot_password?token={password_reset_blob_j_url_safe}"
        ).url

        # Send the email with the reset URL
        await send_email_via_sendgrid(
            to_addresses=[self.email],
            subject="Password Reset Request",
            body=f"""
            Please click on the following link within the next
            15 minutes to reset your password: {password_reset_url}
            """,
        )

    async def verify_password_reset_token(self, token):
        if (
            self.password_reset_token == token
            and self.password_reset_token_expiration >= datetime.utcnow()
        ):
            return True
        else:
            return False
