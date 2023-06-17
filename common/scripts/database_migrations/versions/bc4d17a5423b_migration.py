"""migration

Revision ID: bc4d17a5423b
Revises: 93e416ce2a51
Create Date: 2023-06-12 15:37:31.979203

"""
import sqlalchemy as sa  # noqa: F401
from alembic import op

# revision identifiers, used by Alembic.
revision = "bc4d17a5423b"
down_revision = "93e416ce2a51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uix_change_type_field_key",
        "change_field",
        ["change_type_id", "field_key"],
        unique=True,
    )
    op.create_index(
        "request_pr_idx",
        "request",
        ["tenant_id", "pull_request_id", "repo_name"],
        unique=False,
    )
    op.execute("""ALTER TYPE "RequestStatusEnum" ADD VALUE 'Running';""")
    op.execute("""ALTER TYPE "RequestStatusEnum" ADD VALUE 'Failed';""")


def downgrade() -> None:
    op.drop_index("request_pr_idx", table_name="request")
    op.drop_index("uix_change_type_field_key", table_name="change_field")
    op.execute("""ALTER TYPE "RequestStatusEnum" RENAME TO "RequestStatusEnumOld";""")
    op.execute(
        """CREATE TYPE "RequestStatusEnum" AS ENUM('Pending', 'Approved', 'Rejected', 'Expired');"""
    )
    op.execute(
        """ALTER TABLE request ALTER COLUMN status TYPE "RequestStatusEnum" USING "status::text::RequestStatusEnum";"""
    )
    op.execute("""DROP TYPE "RequestStatusEnumOld";""")
