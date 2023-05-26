import asyncio


async def typeahead_upgrade():
    from sqlalchemy.dialects import postgresql

    from common import TypeAheadFieldHelper
    from common.config.globals import ASYNC_PG_SESSION

    new_typeahead_field_helpers = [
        dict(
            name="S3 Bucket ARN",
            description="Returns a list of S3 bucket ARNs.",
            endpoint="/api/v2/policies/typeahead?resource=s3&show_full_arn_for_s3_buckets=true",
            query_param_key="search",
            provider="aws",
        ),
        dict(
            name="AWS Resource ARN",
            description="Returns a list of all matching AWS resource ARNs.",
            endpoint="/api/v2/typeahead/resources?ui_formatted=true",
            query_param_key="typeahead",
            provider="aws",
        ),
        dict(
            name="IAM Role ARN",
            description="Returns a list of IAM Role ARNs.",
            endpoint="/api/v2/policies/typeahead?resource=iam_arn",
            query_param_key="search",
            provider="aws",
        ),
        dict(
            name="SNS Topic ARN",
            description="Returns a list of SNS Topic ARNs.",
            endpoint="/api/v2/policies/typeahead?resource=sns",
            query_param_key="search",
            provider="aws",
        ),
        dict(
            name="SQS Queue ARN",
            description="Returns a list of SQS Queue ARNs.",
            endpoint="/api/v2/policies/typeahead?resource=sqs",
            query_param_key="search",
            provider="aws",
        ),
        dict(
            name="List AWS services",
            description="Returns a list of AWS services.",
            endpoint="/api/v4/policy-sentry/services",
            query_param_key="service",
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


if __name__ == "__main__":
    asyncio.run(typeahead_upgrade())
