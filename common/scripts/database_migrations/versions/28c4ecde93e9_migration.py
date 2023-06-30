"""migration

Revision ID: 28c4ecde93e9
Revises: c2ef43f9b430
Create Date: 2023-06-28 22:03:36.910594

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "28c4ecde93e9"
down_revision = "1b275666aa9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "iambic_template_provider_definition",
        sa.Column("secondary_resource_id", sa.String(), nullable=True),
    )
    op.create_index(
        "itpd_tenant_resource_idx",
        "iambic_template_provider_definition",
        ["tenant_id", "resource_id"],
        unique=False,
    )
    op.create_index(
        "itpd_tenant_secondary_resource_idx",
        "iambic_template_provider_definition",
        ["tenant_id", "secondary_resource_id"],
        unique=False,
    )

    op.execute(
        """CREATE TYPE "ProviderDefinitionFieldEnum" AS ENUM('Allow One', 'Allow Multiple', 'Allow None');"""
    )
    op.add_column(
        "request_type",
        sa.Column(
            "provider_definition_field",
            postgresql.ENUM(
                "Allow One",
                "Allow Multiple",
                "Allow None",
                name="ProviderDefinitionFieldEnum",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "typeahead_field_helper",
        sa.Column("iambic_template_type", sa.String(), nullable=True),
    )
    op.execute("""ALTER TYPE "FieldTypeEnum" ADD VALUE 'TypeAheadTemplateRef';""")


def downgrade() -> None:
    op.drop_index(
        "itpd_tenant_secondary_resource_idx",
        table_name="iambic_template_provider_definition",
    )
    op.drop_index(
        "itpd_tenant_resource_idx", table_name="iambic_template_provider_definition"
    )
    op.drop_column("iambic_template_provider_definition", "secondary_resource_id")

    op.drop_column("typeahead_field_helper", "iambic_template_type")
    op.drop_column("request_type", "provider_definition_field")
    op.execute("""DROP TYPE "ProviderDefinitionFieldEnum";""")

    # Reverting FieldTypeEnum
    op.execute("""ALTER TYPE "FieldTypeEnum" RENAME TO "FieldTypeEnumOld";""")
    op.execute(
        """CREATE TYPE "FieldTypeEnum" AS ENUM('TextBox', 'TypeAhead', 'EnforcedTypeAhead', 'CheckBox', 'Choice');"""
    )
    op.execute(
        """ALTER TABLE change_field ALTER COLUMN change_type TYPE "FieldTypeEnum" USING "status::text::FieldTypeEnum";"""
    )
    op.execute("""DROP TYPE "FieldTypeEnumOld";""")
