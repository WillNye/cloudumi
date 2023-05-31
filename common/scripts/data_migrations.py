import asyncio


async def typeahead_upgrade():
    from sqlalchemy.dialects import postgresql

    from common import TypeAheadFieldHelper
    from common.config.globals import ASYNC_PG_SESSION

    new_typeahead_field_helpers = [
        dict(
            name="S3 Bucket ARN",
            description="Returns a list of S3 bucket ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/s3",
            query_param_key="resource_arn",
            provider="aws",
        ),
        dict(
            name="AWS Resource ARN",
            description="Returns a list of all matching AWS resource ARNs available to Noq.",
            endpoint="api/v4/self-service/typeahead/aws/service/all",
            query_param_key="resource_arn",
            provider="aws",
        ),
        dict(
            name="IAM Role ARN",
            description="Returns a list of IAM Role ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/iam_role",
            query_param_key="resource_arn",
            provider="aws",
        ),
        dict(
            name="SNS Topic ARN",
            description="Returns a list of SNS Topic ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/sns",
            query_param_key="resource_arn",
            provider="aws",
        ),
        dict(
            name="SQS Queue ARN",
            description="Returns a list of SQS Queue ARNs.",
            endpoint="api/v4/self-service/typeahead/aws/service/sqs",
            query_param_key="resource_arn",
            provider="aws",
        ),
    ]

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = postgresql.insert(TypeAheadFieldHelper).values(
                new_typeahead_field_helpers
            )
            stmt = stmt.on_conflict_do_nothing()

            await session.execute(stmt)
            await session.flush()


def run_data_migrations():
    asyncio.run(typeahead_upgrade())


if __name__ == "__main__":
    run_data_migrations()
