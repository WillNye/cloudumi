"""migration

Revision ID: 28c4ecde93e1
Revises: 28c4ecde93e0
Create Date: 2023-07-12 09:35:36

"""
import sqlalchemy as sa  # noqa: F401
from alembic import op
from sqlalchemy.dialects import postgresql  # noqa: F401

# revision identifiers, used by Alembic.
revision = "28c4ecde93e1"
down_revision = "28c4ecde93e0"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.execute("""ALTER TYPE "RequestStatusEnum" RENAME TO "RequestStatusEnumOld";""")
    op.execute(
        """CREATE TYPE "RequestStatusEnum" AS ENUM('Pending', 'Pending in Git', 'Applied', 'Applying', 'Approved', 'Approving', 'Rejected', 'Expired', 'Failed');"""
    )
    op.execute("""UPDATE request SET status = 'Approved' WHERE status = 'Running';""")
    op.execute(
        """ALTER TABLE request ALTER COLUMN status TYPE "RequestStatusEnum" USING status::text::"RequestStatusEnum";"""
    )
    op.execute("""DROP TYPE "RequestStatusEnumOld";""")


def downgrade() -> None:
    # Reverting RequestStatusEnum
    op.execute("""ALTER TYPE "RequestStatusEnum" RENAME TO "RequestStatusEnumOld";""")
    op.execute(
        """CREATE TYPE "RequestStatusEnum" AS ENUM('Pending', 'Pending in Git', 'Applied', 'Approved', 'Rejected', 'Expired', 'Running', 'Failed');"""
    )
    op.execute(
        """ALTER TABLE request ALTER COLUMN status TYPE "RequestStatusEnum" USING status::text::"RequestStatusEnum";"""
    )
    op.execute("""DROP TYPE "RequestStatusEnumOld";""")
