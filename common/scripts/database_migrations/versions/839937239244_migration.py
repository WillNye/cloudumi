"""migration

Revision ID: 839937239244
Revises: 146467e92abd
Create Date: 2023-03-29 17:28:04.974086

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "839937239244"
down_revision = "146467e92abd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "slack_bots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.String(length=32), nullable=False),
        sa.Column("app_id", sa.String(length=32), nullable=False),
        sa.Column("enterprise_id", sa.String(length=32), nullable=True),
        sa.Column("enterprise_name", sa.String(length=200), nullable=True),
        sa.Column("team_id", sa.String(length=32), nullable=True),
        sa.Column("team_name", sa.String(length=200), nullable=True),
        sa.Column("bot_token", sa.String(length=200), nullable=True),
        sa.Column("bot_id", sa.String(length=32), nullable=True),
        sa.Column("bot_user_id", sa.String(length=32), nullable=True),
        sa.Column("bot_scopes", sa.String(length=1000), nullable=True),
        sa.Column("bot_refresh_token", sa.String(length=200), nullable=True),
        sa.Column("bot_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_enterprise_install", sa.Boolean(), nullable=False),
        sa.Column("installed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "slack_bots_idx",
        "slack_bots",
        ["client_id", "enterprise_id", "team_id", "installed_at"],
        unique=False,
    )
    op.create_table(
        "slack_installations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.String(length=32), nullable=False),
        sa.Column("app_id", sa.String(length=32), nullable=False),
        sa.Column("enterprise_id", sa.String(length=32), nullable=True),
        sa.Column("enterprise_name", sa.String(length=200), nullable=True),
        sa.Column("enterprise_url", sa.String(length=200), nullable=True),
        sa.Column("team_id", sa.String(length=32), nullable=True),
        sa.Column("team_name", sa.String(length=200), nullable=True),
        sa.Column("bot_token", sa.String(length=200), nullable=True),
        sa.Column("bot_id", sa.String(length=32), nullable=True),
        sa.Column("bot_user_id", sa.String(length=32), nullable=True),
        sa.Column("bot_scopes", sa.String(length=1000), nullable=True),
        sa.Column("bot_refresh_token", sa.String(length=200), nullable=True),
        sa.Column("bot_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("user_token", sa.String(length=200), nullable=True),
        sa.Column("user_scopes", sa.String(length=1000), nullable=True),
        sa.Column("user_refresh_token", sa.String(length=200), nullable=True),
        sa.Column("user_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("incoming_webhook_url", sa.String(length=200), nullable=True),
        sa.Column("incoming_webhook_channel", sa.String(length=200), nullable=True),
        sa.Column("incoming_webhook_channel_id", sa.String(length=200), nullable=True),
        sa.Column(
            "incoming_webhook_configuration_url", sa.String(length=200), nullable=True
        ),
        sa.Column("is_enterprise_install", sa.Boolean(), nullable=False),
        sa.Column("token_type", sa.String(length=32), nullable=True),
        sa.Column("installed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "slack_installations_idx",
        "slack_installations",
        ["client_id", "enterprise_id", "team_id", "user_id", "installed_at"],
        unique=False,
    )
    op.create_table(
        "slack_oauth_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("state", sa.String(length=200), nullable=False),
        sa.Column("expire_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "slack_tenant_install_relationships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("slack_bots_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["slack_bots_id"],
            ["slack_bots.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "slack_tenant_oauth_relationships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("oauth_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_slack_tenant"),
    )
    op.create_foreign_key(None, "aws_account", "tenant", ["tenant_id"], ["id"])
    op.add_column(
        "group_memberships", sa.Column("updated_by", sa.String(), nullable=True)
    )
    op.add_column(
        "group_memberships", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column("groups", sa.Column("updated_by", sa.String(), nullable=True))
    op.add_column("groups", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(None, "identity_role", "tenant", ["tenant_id"], ["id"])
    op.add_column("request", sa.Column("pull_request_url", sa.String(), nullable=True))
    op.add_column("request", sa.Column("request_method", sa.String(), nullable=True))
    op.add_column("request", sa.Column("slack_username", sa.String(), nullable=True))
    op.add_column("request", sa.Column("slack_email", sa.String(), nullable=True))
    op.add_column("request", sa.Column("duration", sa.String(), nullable=True))
    op.add_column("request", sa.Column("resource_type", sa.String(), nullable=True))
    op.add_column("request", sa.Column("request_notes", sa.String(), nullable=True))
    op.add_column("request", sa.Column("slack_channel_id", sa.String(), nullable=True))
    op.add_column("request", sa.Column("slack_message_id", sa.String(), nullable=True))
    op.add_column("request", sa.Column("branch_name", sa.String(), nullable=True))
    op.add_column("request", sa.Column("updated_by", sa.String(), nullable=True))
    op.add_column("request", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "request_comment", sa.Column("updated_by", sa.String(), nullable=True)
    )
    op.add_column(
        "request_comment", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column("role_access", sa.Column("updated_by", sa.String(), nullable=True))
    op.add_column("role_access", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(
        None, "role_access", "groups", ["group_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "role_access", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(None, "role_access", "tenant", ["tenant_id"], ["id"])
    op.add_column("tenant", sa.Column("updated_by", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("updated_by", sa.String(), nullable=True))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "updated_at")
    op.drop_column("users", "updated_by")
    op.drop_column("tenant", "updated_at")
    op.drop_column("tenant", "updated_by")
    op.drop_constraint(None, "role_access", type_="foreignkey")
    op.drop_constraint(None, "role_access", type_="foreignkey")
    op.drop_constraint(None, "role_access", type_="foreignkey")
    op.drop_column("role_access", "updated_at")
    op.drop_column("role_access", "updated_by")
    op.drop_column("request_comment", "updated_at")
    op.drop_column("request_comment", "updated_by")
    op.drop_column("request", "updated_at")
    op.drop_column("request", "updated_by")
    op.drop_column("request", "branch_name")
    op.drop_column("request", "slack_message_id")
    op.drop_column("request", "slack_channel_id")
    op.drop_column("request", "request_notes")
    op.drop_column("request", "resource_type")
    op.drop_column("request", "duration")
    op.drop_column("request", "slack_email")
    op.drop_column("request", "slack_username")
    op.drop_column("request", "request_method")
    op.drop_column("request", "pull_request_url")
    op.drop_constraint(None, "identity_role", type_="foreignkey")
    op.drop_column("groups", "updated_at")
    op.drop_column("groups", "updated_by")
    op.drop_column("group_memberships", "updated_at")
    op.drop_column("group_memberships", "updated_by")
    op.drop_constraint(None, "aws_account", type_="foreignkey")
    op.drop_table("slack_tenant_oauth_relationships")
    op.drop_table("slack_tenant_install_relationships")
    op.drop_table("slack_oauth_states")
    op.drop_index("slack_installations_idx", table_name="slack_installations")
    op.drop_table("slack_installations")
    op.drop_index("slack_bots_idx", table_name="slack_bots")
    op.drop_table("slack_bots")
    # ### end Alembic commands ###
