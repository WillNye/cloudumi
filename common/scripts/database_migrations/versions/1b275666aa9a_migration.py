"""migration

Revision ID: 1b275666aa9a
Revises: c5c811930f45
Create Date: 2023-06-27 14:02:09.395315

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1b275666aa9a'
down_revision = 'c5c811930f45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('github_installs_installation_id_key', 'github_installs', type_='unique')
    op.execute("""ALTER TYPE "RequestStatusEnum" ADD VALUE 'Pending in Git';""")


def downgrade() -> None:
    op.create_unique_constraint('github_installs_installation_id_key', 'github_installs', ['installation_id'])

    # Reverting RequestStatusEnum
    op.execute("""ALTER TYPE "RequestStatusEnum" RENAME TO "RequestStatusEnumOld";""")
    op.execute(
        """CREATE TYPE "RequestStatusEnum" AS ENUM('Pending', 'Approved', 'Rejected', 'Expired', 'Running', 'Failed');"""
    )
    op.execute(
        """ALTER TABLE request ALTER COLUMN status TYPE "RequestStatusEnum" USING "status::text::RequestStatusEnum";"""
    )
    op.execute("""DROP TYPE "RequestStatusEnumOld";""")
