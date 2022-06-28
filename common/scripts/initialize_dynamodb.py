# TODO: Dynamo tables should be created via IaC
# TODO: Production should also implement AutoScaling.
# Here is a potential guide:
# https://cols-knil.medium.com/autoscaling-in-dynamodb-with-boto3-bf5bbeb99b10

from botocore.exceptions import ClientError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

import util.debug  # noqa
from common.config import config
from common.config.config import get_dynamo_table_name
from common.lib.aws.session import restricted_get_session_for_saas

streams_enabled = config.get("_global_.dynamodb.streams_enabled", True)
ttl_enabled = config.get("_global_.dynamodb.ttl_enabled", True)

session = restricted_get_session_for_saas()
# TODO: Do we need a boto3 session by tenant here?
ddb = session.client(
    "dynamodb",
    endpoint_url=config.get(
        "_global_.dynamodb_server",
        config.get("_global_.boto3.client_kwargs.endpoint_url"),
    ),
    region_name=config.region,
)

table_name = get_dynamo_table_name("iamroles_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "entity_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "entity_id", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )

except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

if ttl_enabled:
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(
            (
                ddb.exceptions.ResourceNotFoundException,
                ddb.exceptions.ResourceInUseException,
                ClientError,
            )
        ),
    ):
        with attempt:
            try:
                ddb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={
                        "Enabled": True,
                        "AttributeName": "ttl",
                    },
                )
            except Exception as e:
                if str(e) == (
                    "An error occurred (ValidationException) when calling the UpdateTimeToLive operation: "
                    "TimeToLive is already enabled"
                ):
                    pass
                else:
                    print(
                        f"Unable to update TTL attribute on table {table_name}. Error: {e}."
                    )
                    raise

table_name = get_dynamo_table_name("config_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "tenant", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = get_dynamo_table_name("policy_requests_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "request_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "arn-tenant-index",
                "KeySchema": [
                    {"AttributeName": "tenant", "KeyType": "HASH"},
                    {"AttributeName": "arn", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = get_dynamo_table_name("resource_cache_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "entity_id", "KeyType": "RANGE"},  # Sort key
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "entity_id", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant-arn-index",
                "KeySchema": [
                    {"AttributeName": "tenant", "KeyType": "HASH"},
                    {"AttributeName": "arn", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
            {
                "IndexName": "tenant-index",
                "KeySchema": [{"AttributeName": "tenant", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = get_dynamo_table_name("cloudtrail_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "request_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant-arn-index",
                "KeySchema": [
                    {"AttributeName": "tenant", "KeyType": "HASH"},
                    {"AttributeName": "arn", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
        ],
    )

except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

if ttl_enabled:
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(
            (
                ddb.exceptions.ResourceNotFoundException,
                ddb.exceptions.ResourceInUseException,
                ClientError,
            )
        ),
    ):
        with attempt:
            try:
                ddb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={
                        "Enabled": True,
                        "AttributeName": "ttl",
                    },
                )
            except Exception as e:
                if str(e) == (
                    "An error occurred (ValidationException) when calling the UpdateTimeToLive operation: "
                    "TimeToLive is already enabled"
                ):
                    pass
                else:
                    print(
                        f"Unable to update TTL attribute on table {table_name}. Error: {e}."
                    )
                    raise

try:
    table_name = get_dynamo_table_name("users_multitenant")
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "username", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")


table_name = get_dynamo_table_name("notifications_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "predictable_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "predictable_id", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )

except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")


table_name = get_dynamo_table_name("tenant_static_configs")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "tenant", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = get_dynamo_table_name("identity_groups_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "group_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "group_id", "AttributeType": "S"},
            {"AttributeName": "tenant", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = get_dynamo_table_name("identity_users_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "user_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = get_dynamo_table_name("identity_requests_multitenant")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "request_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "tenant", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = "noq_api_keys"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "api_key", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "api_key", "AttributeType": "S"},
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "id", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
            {
                "IndexName": "tenant_id_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                    {
                        "AttributeName": "id",
                        "KeyType": "RANGE",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
        ],
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

if ttl_enabled:
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(
            (
                ddb.exceptions.ResourceNotFoundException,
                ddb.exceptions.ResourceInUseException,
                ClientError,
            )
        ),
    ):
        with attempt:
            try:
                ddb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={
                        "Enabled": True,
                        "AttributeName": "ttl",
                    },
                )
            except Exception as e:
                if str(e) == (
                    "An error occurred (ValidationException) when calling the UpdateTimeToLive operation: "
                    "TimeToLive is already enabled"
                ):
                    pass
                else:
                    print(
                        f"Unable to update TTL attribute on table {table_name}. Error: {e}."
                    )

table_name = get_dynamo_table_name("aws_accounts")
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "aws_account_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "aws_account_id", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "tenant_index",
                "KeySchema": [
                    {
                        "AttributeName": "tenant",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
            {
                "IndexName": "aws_account_id_index",
                "KeySchema": [
                    {
                        "AttributeName": "aws_account_id",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
        ],
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")
