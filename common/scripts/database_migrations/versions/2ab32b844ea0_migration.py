"""migration

Revision ID: 2ab32b844ea0
Revises: 416377939322
Create Date: 2023-01-28 13:20:12.072433

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2ab32b844ea0"
down_revision = "416377939322"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "slack_tenant_install_relationships",
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("slack_bots_id", sa.Integer(), nullable=True),
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
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("slack_tenant_install_relationships")
    # ### end Alembic commands ###
