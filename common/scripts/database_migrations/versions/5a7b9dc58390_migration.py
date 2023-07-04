"""migration

Revision ID: 5a7b9dc58390
Revises: 1b275666aa9a
Create Date: 2023-07-03 15:44:52.201361

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5a7b9dc58390"
down_revision = "1b275666aa9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("request", sa.Column("justification", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("request", "justification")
