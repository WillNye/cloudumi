import asyncio

from iambic.plugins.v0_1_0.okta.user.models import OKTA_USER_TEMPLATE_TYPE
from sqlalchemy import or_


async def typeahead_upgrade():
    from sqlalchemy.dialects import postgresql

    from common.config.globals import ASYNC_PG_SESSION
    from common.request_types.models import TypeAheadFieldHelper

    aws_typeahead_field_helpers = [
        dict(
            name="S3 Bucket ARN",
            description="Returns a list of S3 bucket ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/s3",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="AWS Resource ARN",
            description="Returns a list of all matching AWS resource ARNs available to Noq.",
            endpoint="api/v4/self-service/typeahead/aws/service/all",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="IAM Role ARN",
            description="Returns a list of IAM Role ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/iam_role",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="SNS Topic ARN",
            description="Returns a list of SNS Topic ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/sns",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="SQS Queue ARN",
            description="Returns a list of SQS Queue ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/sqs",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="AWS only Managed Policies",
            description="Returns a list of IAM policies managed by AWS.",
            endpoint="api/v4/self-service/typeahead/aws/service/managed_policy?aws_managed_only=true",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="AWS and Customer Managed Policies",
            description="Returns a list of IAM policies.",
            endpoint="api/v4/self-service/typeahead/aws/service/managed_policy",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="Customer Managed Policy Template Refs",
            description="Returns a list of IAM policies.",
            endpoint="api/v4/self-service/template-ref/aws/service/managed_policy",
            query_param_key="resource_id",
            provider="aws",
        ),
        dict(
            name="Noq Group",
            description="Returns a list of Noq Group names.",
            endpoint="api/v4/self-service/typeahead/noq/groups",
            query_param_key="name",
            provider="aws",
        ),
        dict(
            name="Noq User",
            description="Returns a list of Noq User E-Mail addresses.",
            endpoint="api/v4/self-service/typeahead/noq/users",
            query_param_key="email",
            provider="aws",
        ),
    ]

    okta_typeahead_field_helpers = [
        dict(
            name="Okta User",
            description="Returns a list of Okta User E-Mail addresses",
            endpoint="api/v4/self-service/typeahead/okta/users",
            query_param_key="email",
            provider="okta",
        )
    ]

    default_typeahead_field_helpers = [
        *aws_typeahead_field_helpers,
        *okta_typeahead_field_helpers,
    ]

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for row in default_typeahead_field_helpers:
                stmt = postgresql.insert(TypeAheadFieldHelper).values(row)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["provider", "endpoint"], set_=row
                )
                await session.execute(stmt)
            await session.flush()


async def iambic_template_add_friendly_name():
    from iambic.plugins.v0_1_0.okta.app.models import OKTA_APP_TEMPLATE_TYPE
    from iambic.plugins.v0_1_0.okta.group.models import OKTA_GROUP_TEMPLATE_TYPE
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from common.config.globals import ASYNC_PG_SESSION
    from common.iambic.templates.models import IambicTemplate

    async with ASYNC_PG_SESSION() as session:
        items = await session.execute(
            select(IambicTemplate)
            .options(
                joinedload(IambicTemplate.content)
            )  # Adjusted to use class-bound attribute
            .where(
                or_(
                    IambicTemplate.friendly_name.is_(None),
                    IambicTemplate.friendly_name == IambicTemplate.resource_id,
                )
            )
        )
        iambic_templates_without_friendly_name = items.scalars().all()

    for iambic_template in iambic_templates_without_friendly_name:
        # TODO: duplicated logic
        if iambic_template.template_type in [
            OKTA_GROUP_TEMPLATE_TYPE,
            OKTA_APP_TEMPLATE_TYPE,
        ]:
            iambic_template_content = iambic_template.content.content
            friendly_name = iambic_template_content.get("properties", {}).get(
                "name", iambic_template.resource_id
            )
            iambic_template.friendly_name = friendly_name
        elif iambic_template.template_type in [OKTA_USER_TEMPLATE_TYPE]:
            iambic_template_content = iambic_template.content.content
            friendly_name = iambic_template_content.get("properties", {}).get(
                "username", iambic_template.resource_id
            )
            iambic_template.friendly_name = friendly_name
        elif iambic_template.friendly_name != iambic_template.resource_id:
            iambic_template.friendly_name = iambic_template.resource_id
        else:
            continue

        await iambic_template.write()


def run_data_migrations():
    asyncio.run(typeahead_upgrade())
    asyncio.run(iambic_template_add_friendly_name())


if __name__ == "__main__":
    run_data_migrations()
