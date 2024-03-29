"""migration

Revision ID: c5c811930f45
Revises: 93e416ce2a51
Create Date: 2023-06-08 13:37:08.941312

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.sql.sqltypes import Enum

# revision identifiers, used by Alembic.
revision = "c5c811930f45"
down_revision = "0d66940df8e4"
branch_labels = None
depends_on = None

old_enum = ENUM("MANUAL", "SCIM", name="managed_by_enum", create_type=False)
new_enum = ENUM("MANUAL", "SCIM", "SSO", name="managed_by_enum", create_type=False)

tmp_enum_users = ENUM(
    "MANUAL", "SCIM", "SSO", name="_managed_by_enum_users", create_type=False
)
tmp_enum_groups = ENUM(
    "MANUAL", "SCIM", "SSO", name="_managed_by_enum_groups", create_type=False
)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("users", sa.Column("description", sa.String(), nullable=True))

    # Create a temporary enum type
    temp_enum = Enum("MANUAL", "SCIM", "SSO", name="temp_managed_by_enum")
    temp_enum.create(op.get_bind(), checkfirst=False)

    # Handle users table
    op.execute(
        "ALTER TABLE users ALTER COLUMN managed_by TYPE temp_managed_by_enum USING managed_by::text::temp_managed_by_enum"
    )

    # Handle groups table
    op.execute(
        "ALTER TABLE groups ALTER COLUMN managed_by TYPE temp_managed_by_enum USING managed_by::text::temp_managed_by_enum"
    )

    # Drop the old enum type
    op.execute("DROP TYPE managed_by_enum")

    # Rename the temporary enum type to the old name
    op.execute("ALTER TYPE temp_managed_by_enum RENAME TO managed_by_enum")
    op.drop_index("ix_tenant_name", table_name="tenant")
    op.create_index(op.f("ix_tenant_name"), "tenant", ["name"], unique=True)
    op.create_unique_constraint(None, "tenant", ["organization_id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "tenant", type_="unique")
    op.drop_index(op.f("ix_tenant_name"), table_name="tenant")
    op.create_index("ix_tenant_name", "tenant", ["name"], unique=False)
    op.drop_column("users", "description")

    # Create a temporary enum type
    temp_enum = sa.Enum("MANUAL", "SCIM", name="temp_managed_by_enum")
    temp_enum.create(op.get_bind(), checkfirst=False)

    # Handle users table
    op.execute(
        "ALTER TABLE users ALTER COLUMN managed_by TYPE temp_managed_by_enum USING managed_by::text::temp_managed_by_enum"
    )

    # Handle groups table
    op.execute(
        "ALTER TABLE groups ALTER COLUMN managed_by TYPE temp_managed_by_enum USING managed_by::text::temp_managed_by_enum"
    )

    # Drop the old enum type
    op.execute("DROP TYPE managed_by_enum")

    # Create the old enum type again
    op.execute(
        """
    DO $$
    BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'managed_by_enum') THEN
        CREATE TYPE managed_by_enum AS ENUM ('MANUAL', 'SCIM');
    END IF;
    END $$;
    """
    )

    # Convert columns back to the old enum type
    op.execute(
        "ALTER TABLE users ALTER COLUMN managed_by TYPE managed_by_enum USING managed_by::text::managed_by_enum"
    )
    op.execute(
        "ALTER TABLE groups ALTER COLUMN managed_by TYPE managed_by_enum USING managed_by::text::managed_by_enum"
    )

    # Drop the temporary enum type
    op.execute("DROP TYPE temp_managed_by_enum")
    # ### end Alembic commands ###
