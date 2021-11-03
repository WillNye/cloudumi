from botocore.exceptions import ClientError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from cloudumi_common.config import config
from cloudumi_common.lib.aws.session import restricted_get_session_for_saas

streams_enabled = config.get("_global_.dynamodb.streams_enabled", True)
ttl_enabled = config.get("_global_.dynamodb.ttl_enabled", True)

session = restricted_get_session_for_saas()
# TODO: Do we need a boto3 session by host here?
ddb = session.client(
    "dynamodb",
    endpoint_url=config.get(
        "_global_.dynamodb_server",
        config.get("_global_.boto3.client_kwargs.endpoint_url"),
    ),
    region_name=config.region,
)

table_name = "consoleme_iamroles_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "host", "AttributeType": "S"},
            {"AttributeName": "entity_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "entity_id", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "host_index",
                "KeySchema": [
                    {
                        "AttributeName": "host",
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

    if ttl_enabled:
        try:
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
                    ddb.update_time_to_live(
                        TableName=table_name,
                        TimeToLiveSpecification={
                            "Enabled": True,
                            "AttributeName": "ttl",
                        },
                    )
        except ClientError as e:
            if str(e) != (
                "An error occurred (ValidationException) when calling the UpdateTimeToLive operation: "
                "TimeToLive is already enabled"
            ):
                print(
                    f"Unable to update TTL attribute on table {table_name}. Error: {e}."
                )

except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = "consoleme_config_multitenant"
try:
    ddb.create_table(
        TableName="consoleme_config_multitenant",
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "host", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "host_index",
                "KeySchema": [
                    {
                        "AttributeName": "host",
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

table_name = "consoleme_policy_requests_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "request_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "host", "AttributeType": "S"},
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "arn-host-index",
                "KeySchema": [
                    {"AttributeName": "host", "KeyType": "HASH"},
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

table_name = "consoleme_resource_cache_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "entity_id", "KeyType": "RANGE"},  # Sort key
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "host", "AttributeType": "S"},
            {"AttributeName": "entity_id", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "host-arn-index",
                "KeySchema": [
                    {"AttributeName": "host", "KeyType": "HASH"},
                    {"AttributeName": "arn", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
            {
                "IndexName": "host-index",
                "KeySchema": [{"AttributeName": "host", "KeyType": "HASH"}],
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

table_name = "consoleme_cloudtrail_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "arn", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "host", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
    if ttl_enabled:
        try:
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
                    ddb.update_time_to_live(
                        TableName=table_name,
                        TimeToLiveSpecification={
                            "Enabled": True,
                            "AttributeName": "ttl",
                        },
                    )
        except ClientError as e:
            if str(e) != (
                "An error occurred (ValidationException) when calling the UpdateTimeToLive operation: "
                "TimeToLive is already enabled"
            ):
                print(
                    f"Unable to update TTL attribute on table {table_name}. Error: {e}."
                )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

try:
    table_name = "consoleme_users_multitenant"
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "username", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "host", "AttributeType": "S"},
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


table_name = "consoleme_notifications_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "host", "AttributeType": "S"},
            {"AttributeName": "predictable_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
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


table_name = "consoleme_tenant_static_configs"
try:
    ddb.create_table(
        TableName="consoleme_tenant_static_configs",
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "host", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "host_index",
                "KeySchema": [
                    {
                        "AttributeName": "host",
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

table_name = "consoleme_identity_groups_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "group_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "group_id", "AttributeType": "S"},
            {"AttributeName": "host", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "host_index",
                "KeySchema": [
                    {
                        "AttributeName": "host",
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

table_name = "consoleme_identity_users_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "host", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "host_index",
                "KeySchema": [
                    {
                        "AttributeName": "host",
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

table_name = "consoleme_identity_requests_multitenant"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "host", "KeyType": "HASH"},
            {"AttributeName": "request_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "host", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        StreamSpecification={
            "StreamEnabled": streams_enabled,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
        GlobalSecondaryIndexes=[
            {
                "IndexName": "host_index",
                "KeySchema": [
                    {
                        "AttributeName": "host",
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
