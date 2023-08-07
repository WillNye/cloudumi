"""migration

Revision ID: c0372c6cde5b
Revises: 28c4ecde93e1
Create Date: 2023-08-01 14:15:14.901537

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c0372c6cde5b"
down_revision = "28c4ecde93e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "revert_request_reference",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_request_id", sa.UUID(), nullable=False),
        sa.Column("revert_request_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["revert_request_id"],
            ["request.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_request_id"],
            ["request.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revert_request_id"),
        sa.UniqueConstraint("target_request_id"),
    )
    # ### end Alembic commands ###
    op.execute("""ALTER TYPE "RequestStatusEnum" ADD VALUE 'Reverted';""")


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("revert_request_reference")
    # ### end Alembic commands ###
    op.execute("""ALTER TYPE "RequestStatusEnum" RENAME TO "RequestStatusEnumOld";""")
    op.execute(
        """CREATE TYPE "RequestStatusEnum" AS ENUM('Pending', 'Pending in Git', 'Applied', 'Applying', 'Approving', 'Approved', 'Rejected', 'Expired', 'Failed');"""
    )
    op.execute(
        """ALTER TABLE request ALTER COLUMN status TYPE "RequestStatusEnum" USING status::text::"RequestStatusEnum";"""
    )
    op.execute("""DROP TYPE "RequestStatusEnumOld";""")
