"""migration

Revision ID: f197014060b6
Revises: 82d249e52311
Create Date: 2022-12-28 10:04:33.172263

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f197014060b6"
down_revision = "82d249e52311"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "groups",
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("tenant", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant", "email", name="uq_group_tenant_email"),
        sa.UniqueConstraint("tenant", "name", name="uq_tenant_name"),
    )
    op.create_table(
        "users",
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=True),
        sa.Column("email_verify_token", sa.String(), nullable=True),
        sa.Column("email_verify_token_expiration", sa.DateTime(), nullable=True),
        sa.Column("password_reset_required", sa.Boolean(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("password_reset_token", sa.String(), nullable=True),
        sa.Column("password_reset_token_expiration", sa.DateTime(), nullable=True),
        sa.Column("login_attempts", sa.Integer(), nullable=True),
        sa.Column("login_magic_link_token", sa.String(), nullable=True),
        sa.Column("login_magic_link_token_expiration", sa.DateTime(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("mfa_secret", sa.String(), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=True),
        sa.Column("mfa_primary_method", sa.String(length=64), nullable=True),
        sa.Column("mfa_phone_number", sa.String(length=128), nullable=True),
        sa.Column("last_successful_mfa_code", sa.String(length=64), nullable=True),
        sa.Column("tenant", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant", "email", name="uq_tenant_email"),
        sa.UniqueConstraint("tenant", "username", name="uq_tenant_username"),
    )
    op.create_table(
        "group_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("group_memberships")
    op.drop_table("users")
    op.drop_table("groups")
    # ### end Alembic commands ###
