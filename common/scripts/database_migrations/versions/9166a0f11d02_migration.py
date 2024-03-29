"""migration

Revision ID: 9166a0f11d02
Revises: 839937239244
Create Date: 2023-05-01 12:49:22.809308

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "9166a0f11d02"
down_revision = "839937239244"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, "aws_account", "tenant", ["tenant_id"], ["id"])
    op.create_foreign_key(None, "identity_role", "tenant", ["tenant_id"], ["id"])
    op.create_foreign_key(None, "request", "tenant", ["tenant_id"], ["id"])
    op.create_foreign_key(
        None, "role_access", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "role_access", "groups", ["group_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(None, "role_access", "tenant", ["tenant_id"], ["id"])
    op.create_foreign_key(
        None, "slack_tenant_install_relationships", "tenant", ["tenant_id"], ["id"]
    )
    op.create_foreign_key(
        None, "slack_tenant_oauth_relationships", "tenant", ["tenant_id"], ["id"]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "slack_tenant_oauth_relationships", type_="foreignkey")
    op.drop_constraint(None, "slack_tenant_install_relationships", type_="foreignkey")
    op.drop_constraint(None, "role_access", type_="foreignkey")
    op.drop_constraint(None, "role_access", type_="foreignkey")
    op.drop_constraint(None, "role_access", type_="foreignkey")
    op.drop_constraint(None, "request", type_="foreignkey")
    op.drop_constraint(None, "identity_role", type_="foreignkey")
    op.drop_constraint(None, "aws_account", type_="foreignkey")
    # ### end Alembic commands ###
