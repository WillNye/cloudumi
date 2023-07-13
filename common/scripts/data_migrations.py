import asyncio


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
    default_typeahead_field_helpers = aws_typeahead_field_helpers

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for row in default_typeahead_field_helpers:
                stmt = postgresql.insert(TypeAheadFieldHelper).values(row)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["provider", "endpoint"], set_=row
                )
                await session.execute(stmt)
            await session.flush()


def run_data_migrations():
    asyncio.run(typeahead_upgrade())


if __name__ == "__main__":
    run_data_migrations()
