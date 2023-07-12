"""migration

Revision ID: 28c4ecde93e0
Revises: 28c4ecde93e9
Create Date: 2023-07-12 09:35:36

"""
import sqlalchemy as sa  # noqa: F401
from alembic import op
from sqlalchemy.dialects import postgresql  # noqa: F401

# revision identifiers, used by Alembic.
revision = "28c4ecde93e0"
down_revision = "28c4ecde93e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""ALTER TYPE "RequestStatusEnum" ADD VALUE 'Applied';""")


def downgrade() -> None:
    # Reverting RequestStatusEnum
    op.execute("""ALTER TYPE "RequestStatusEnum" RENAME TO "RequestStatusEnumOld";""")
    op.execute(
        """CREATE TYPE "RequestStatusEnum" AS ENUM('Pending', 'Pending in Git', 'Approved', 'Rejected', 'Expired', 'Running', 'Failed');"""
    )
    op.execute(
        """ALTER TABLE request ALTER COLUMN status TYPE "RequestStatusEnum" USING "status::text::RequestStatusEnum";"""
    )
    op.execute("""DROP TYPE "RequestStatusEnumOld";""")
