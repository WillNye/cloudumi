import asyncio
import json
import os
import random
import unittest
import uuid
from datetime import datetime

import boto3
import fakeredis
import pytest
from asgiref.sync import async_to_sync
from mock import MagicMock, Mock, patch
from moto import (
    mock_config,
    mock_dynamodb,
    mock_iam,
    mock_s3,
    mock_ses,
    mock_sns,
    mock_sqs,
    mock_sts,
)
from tornado.concurrent import Future

# Unit tests will create mock resources in us-east-1
from util.tests.fixtures.globals import tenant

os.environ["AWS_REGION"] = "us-east-1"
os.environ["ASYNC_TEST_TIMEOUT"] = "100"

# This must be set before loading NOQ's configuration
if not os.environ.get("CONFIG_LOCATION"):
    os.environ["CONFIG_LOCATION"] = "util/tests/test_configuration.yaml"

MOCK_ROLE = {
    "arn": "arn:aws:iam::123456789012:role/FakeRole",
    "name": "FakeRole",
    "accountId": "123456789012",
    "policy": {
        "Path": "/",
        "RoleId": "ABCDEFG",
        "Arn": "arn:aws:iam::123456789012:role/FakeRole",
        "CreateDate": "2019-01-15T22:55:53Z",
        "AssumeRolePolicyDocument": {
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Sid": "2",
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:role/FakeRole"},
                    "Action": "sts:AssumeRole",
                },
                {
                    "Sid": "1",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:role/ConsoleMeInstanceProfile"
                    },
                    "Action": "sts:AssumeRole",
                },
            ],
        },
        "Tags": [],
        "AttachedManagedPolicies": [
            {
                "PolicyName": "test1-Example.com",
                "PolicyArn": "arn:aws:iam::123456789012:policy/testPolicy",
            }
        ],
        "InstanceProfileList": [],
        "RolePolicyList": [
            {
                "PolicyName": "iam",
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "iam:GetAccountAuthorizationDetails",
                                "iam:GetRole",
                                "iam:GetRolePolicy",
                                "iam:ListInstanceProfiles",
                                "iam:ListInstanceProfilesForRole",
                                "iam:ListRolePolicies",
                                "iam:ListRoles",
                                "iam:ListAttachedRolePolicies",
                                "iam:ListRoleTags",
                                "s3:listallmybuckets",
                                "sqs:ListQueues",
                                "sqs:getqueueattributes",
                                "sns:ListTopics",
                            ],
                            "Effect": "Allow",
                            "Resource": ["*"],
                            "Sid": "iam",
                        }
                    ],
                    "Version": "2012-10-17",
                },
            }
        ],
    },
    "templated": "fake/file.json",
}

MOCK_REDIS_DB_PATH = f"/tmp/cloudumi_unit_test_{str(uuid.uuid4())}.rdb"

all_roles = None


class AioTestCase(unittest.TestCase):

    # noinspection PyPep8Naming
    def __init__(self, methodName="runTest", loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._function_cache = {}
        super(AioTestCase, self).__init__(methodName=methodName)

    def coroutine_function_decorator(self, func):
        def wrapper(*args, **kw):
            return self.loop.run_until_complete(func(*args, **kw))

        return wrapper

    def __getattribute__(self, item):
        attr = object.__getattribute__(self, item)
        if asyncio.iscoroutinefunction(attr):
            if item not in self._function_cache:
                self._function_cache[item] = self.coroutine_function_decorator(attr)
            return self._function_cache[item]
        return attr


class MockBaseMtlsHandler:
    async def authorization_flow_user(self):
        self.request_uuid = 1234
        self.ip = "1.2.3.4"
        self.requester = {"type": "user"}

    async def authorization_flow_app(self):
        self.request_uuid = 1234
        self.ip = "1.2.3.4"
        self.requester = {"type": "application", "name": "fakeapp"}


class MockAuth:
    def __init__(
        self, restricted=False, compliance_restricted=False, get_groups_val=None
    ):
        if get_groups_val is None:
            get_groups_val = []
        self.restricted = restricted
        self.compliance_restricted = compliance_restricted
        self.get_groups_val = get_groups_val

    async def get_groups(self, *kvargs):
        return self.get_groups_val


class MockRedis:
    def __init__(self, return_value=None):
        self.return_value = return_value

    def get(self, tag):
        print(f"MockRedis GET called with argument {tag}")
        return self.return_value

    def setex(self, *args):
        print(f"MockRedis SETEX called with args {args}")

    def hgetall(self, *args):
        print(f"MockRedis HGETALL called with args {args}")
        return self.return_value


class MockRedisHandler:
    def __init__(self, return_value=None):
        self.return_value = return_value

    async def redis(self):
        redis_client = MockRedis(return_value=self.return_value)
        return redis_client


mock_accountdata_redis = MagicMock(
    return_value=MockRedisHandler(
        return_value=json.dumps(
            {"123456789012": ["awsaccount", "awsaccount@example.com"]}
        )
    )
)


class AWSHelper:
    async def random_account_id(self):
        return str(random.randrange(100000000000, 999999999999))


mock_get_by_name_sync_fn = MagicMock(return_value=tenant)


@pytest.fixture(autouse=True, scope="session")
def mock_get_by_name_sync():
    with patch("common.tenants.models.Tenant.get_by_name_sync", new_callable=MagicMock):
        yield mock_get_by_name_sync_fn


@pytest.fixture(autouse=False, scope="session")
def redis_prereqs(redis):
    from common.lib.redis import RedisHandler

    red = RedisHandler().redis_sync(tenant)
    red.hmset(
        f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
        {
            "arn:aws:ec2:us-west-2:123456789013:security-group/12345": json.dumps(
                {
                    "resourceType": "AWS::EC2::SecurityGroup",
                }
            ),
            "arn:aws:sqs:us-east-1:123456789012:rolequeue": json.dumps(
                {
                    "resourceType": "AWS::SQS::Queue",
                }
            ),
            "arn:aws:sns:us-east-1:123456789012:roletopic": json.dumps(
                {
                    "resourceType": "AWS::SNS::Topic",
                }
            ),
            "arn:aws:iam::123456789012:role/role": json.dumps(
                {
                    "resourceType": "AWS::IAM::Role",
                }
            ),
        },
    )


@pytest.fixture(autouse=False, scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(autouse=False, scope="session")
def sts(aws_credentials):
    """Mocked STS Fixture."""
    from common.config import config

    with mock_sts():
        yield boto3.client(
            "sts",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )


@pytest.fixture(autouse=False, scope="session")
def ec2(aws_credentials):
    """Mocked ec2 Fixture."""
    from common.config import config

    with mock_sts():
        yield boto3.client(
            "ec2",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )


@pytest.fixture(autouse=False, scope="session")
def iam(aws_credentials):
    """Mocked IAM Fixture."""
    from common.config import config

    with mock_iam():
        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )
        client.create_role(
            RoleName="roleA",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )
        yield client


@pytest.fixture(autouse=False, scope="session")
def aws_config(aws_credentials):
    """Mocked Config Fixture."""
    from common.config import config

    with mock_config():
        yield boto3.client(
            "config",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )


@pytest.fixture(autouse=False, scope="session")
def s3(aws_credentials, dynamodb):
    """Mocked S3 Fixture."""
    from common.config import config

    with mock_s3():
        yield boto3.client(
            "s3",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )


@pytest.fixture(autouse=False, scope="session")
def ses(aws_credentials):
    """Mocked SES Fixture."""
    from common.config import config

    with mock_ses():
        client = boto3.client(
            "ses",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )
        client.verify_email_address(EmailAddress="consoleme_test@example.com")
        yield client


@pytest.fixture(autouse=False, scope="session")
def sqs(aws_credentials):
    """Mocked SQS Fixture."""
    from common.config import config

    with mock_sqs():
        yield boto3.client(
            "sqs",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )


@pytest.fixture(autouse=False, scope="session")
def sns(aws_credentials):
    """Mocked S3 Fixture."""
    from common.config import config

    with mock_sns():
        yield boto3.client(
            "sns",
            region_name="us-east-1",
            **config.get("_global_.boto3.client_kwargs", {}),
        )


@pytest.fixture(autouse=False, scope="session")
def create_default_resources(s3, iam, sts, redis, iam_sync_principals, iamrole_table):
    from asgiref.sync import async_to_sync

    from common.config import config
    from common.lib.cache import store_json_results_in_redis_and_s3

    global all_roles
    buckets = [
        config.get_tenant_specific_key(
            "s3_cache_bucket",
            tenant,
            config.get("_global_.s3_cache_bucket"),
        )
    ]
    for bucket in buckets:
        s3.create_bucket(Bucket=bucket)

    if all_roles:
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_roles,
            s3_bucket=config.get_tenant_specific_key(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket",
                tenant,
            ),
            s3_key=config.get_tenant_specific_key(
                "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
                tenant,
                "account_resource_cache/cache_all_roles_v1.json.gz",
            ),
            tenant=tenant,
        )
        return
    from common.celery_tasks.celery_tasks import cache_iam_resources_for_account
    from common.lib.account_indexers import get_account_id_to_name_mapping
    from common.lib.redis import RedisHandler

    red = RedisHandler().redis_sync(tenant)

    accounts_d = async_to_sync(get_account_id_to_name_mapping)(tenant)
    for account_id in accounts_d.keys():
        cache_iam_resources_for_account(account_id, tenant=tenant)

    cache_key = config.get_tenant_specific_key(
        "aws.iamroles_redis_key", tenant, f"{tenant}_IAM_ROLE_CACHE"
    )
    all_roles = red.hgetall(cache_key)
    async_to_sync(store_json_results_in_redis_and_s3)(
        all_roles,
        s3_bucket=config.get_tenant_specific_key(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket",
            tenant,
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
            tenant,
            "account_resource_cache/cache_all_roles_v1.json.gz",
        ),
        tenant=tenant,
    )


@pytest.fixture(autouse=False, scope="session")
def dynamodb(aws_credentials):
    """Mocked DynamoDB Fixture."""
    with mock_dynamodb():
        # Remove the config value for the DynamoDB Server
        from common.config.config import CONFIG

        old_value = CONFIG.config.pop("_global_.dynamodb_server", None)

        yield boto3.client(
            "dynamodb",
            region_name="us-east-1",
            **CONFIG.get("_global_.boto3.client_kwargs", {}),
        )

        # Reset the config value:
        CONFIG.config["_global_"]["dynamodb_server"] = old_value


@pytest.fixture(autouse=False, scope="session")
def retry():
    """Mock the retry library so that it doesn't retry."""

    class MockRetry:
        def __init__(self, *args, **kwargs):
            pass

        def call(self, f, *args, **kwargs):
            return f(*args, **kwargs)

    patch_retry = patch("retrying.Retrying", MockRetry)
    yield patch_retry.start()

    patch_retry.stop()


@pytest.fixture(autouse=False, scope="session")
def iamrole_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="iamroles_multitenant",
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "entity_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "entity_id", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield dynamodb


@pytest.fixture(autouse=True, scope="session")
def tenant_details_table(dynamodb):
    table_name = "tenant_details"
    # Create the table:
    table_obj = dynamodb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "name", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "name", "KeyType": "HASH"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield table_obj


@pytest.fixture(autouse=False, scope="session")
def cloudtrail_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="cloudtrail_multitenant",
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "arn", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )

    # Apply a TTL:
    dynamodb.update_time_to_live(
        TableName="cloudtrail_multitenant",
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
    )

    yield dynamodb


@pytest.fixture(autouse=False, scope="session")
def sqs_queue(sqs):
    sqs.create_queue(
        QueueName="consoleme-cloudtrail-role-events-test",
    )
    sqs.create_queue(QueueName="consoleme-cloudtrail-access-deny-events-test")

    queue_url = sqs.get_queue_url(QueueName="consoleme-cloudtrail-role-events-test")
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    # Event Bridge -> SNS -> SQS message format
    message = json.dumps(
        {
            "Message": json.dumps(
                {
                    "version": "0",
                    "id": "825688d9-11c0-e149-0ef0-7c996f7f1468",
                    "detail-type": "AWS API Call via CloudTrail",
                    "source": "aws.iam",
                    "account": "123456789012",
                    "time": "2021-06-15T18:51:57Z",
                    "region": "us-east-1",
                    "resources": [],
                    "detail": {
                        "eventVersion": "1.08",
                        "userIdentity": {
                            "type": "AssumedRole",
                            "principalId": "ABC123:i-12345",
                            "arn": "arn:aws:sts::123456789012:assumed-role/role1/3957",
                            "accountId": "123456789012",
                            "accessKeyId": "ACESSKEYID",
                            "sessionContext": {
                                "sessionIssuer": {
                                    "type": "Role",
                                    "principalId": "PRINCIPALID",
                                    "arn": "arn:aws:iam::123456789012:role/role1",
                                    "accountId": "123456789012",
                                    "userName": "role1",
                                },
                                "webIdFederationData": {},
                                "attributes": {
                                    "creationDate": "2021-06-15T18:51:56Z",
                                    "mfaAuthenticated": "false",
                                },
                            },
                        },
                        "errorCode": "AccessDenied",
                        "eventTime": current_time,
                        "eventSource": "iam.amazonaws.com",
                        "eventName": "AttachRolePolicy",
                        "awsRegion": "us-east-1",
                        "sourceIPAddress": "1.2.3.4",
                        "userAgent": "Botocore",
                        "requestParameters": {
                            "roleName": "role1",
                            "policyArn": "arn:aws:iam::123456789012:policy/1",
                        },
                        "responseElements": None,
                        "requestID": "22ba2e61-aae9-4a8f-80af-e1d20d3b07b5",
                        "eventID": "2ee753fa-c79c-4b2a-9584-7a011d6fe763",
                        "readOnly": False,
                        "eventType": "AwsApiCall",
                        "managementEvent": True,
                        "recipientAccountId": "123456789012",
                        "eventCategory": "Management",
                    },
                }
            )
        }
    )
    sqs.send_message(QueueUrl=queue_url["QueueUrl"], MessageBody=message)

    # Event Bridge -> SQS message format
    message = json.dumps(
        {
            "version": "0",
            "id": "11111-39b0-3218-d06d-a529b9da5b75",
            "detail-type": "AWS API Call via CloudTrail",
            "source": "aws.iam",
            "account": "123456789012",
            "time": "2021-09-03T20:16:32Z",
            "region": "us-east-1",
            "resources": [],
            "detail": {
                "eventVersion": "1.08",
                "userIdentity": {
                    "type": "AssumedRole",
                    "principalId": "ABC123:i-12345",
                    "arn": "arn:aws:sts::123456789012:assumed-role/aRole/thatDoesSomething",
                    "accountId": "123456789012",
                    "accessKeyId": "ACCESS_KEY",
                    "sessionContext": {
                        "sessionIssuer": {
                            "type": "Role",
                            "principalId": "PRINCIPAL_ID",
                            "arn": "arn:aws:iam::123456789012:role/aRole",
                            "accountId": "123456789012",
                            "userName": "aRole",
                        },
                        "webIdFederationData": {},
                        "attributes": {
                            "creationDate": "2021-09-03T20:16:32Z",
                            "mfaAuthenticated": "false",
                        },
                    },
                },
                "errorCode": "AccessDenied",
                "eventTime": current_time,
                "eventSource": "iam.amazonaws.com",
                "eventName": "TagRole",
                "awsRegion": "us-east-1",
                "sourceIPAddress": "1.2.3.4",
                "userAgent": "Boto3/1.18.36 Python/3.7.11 Linux/4.14.243-194.434.amzn2.x86_64 exec-env/AWS_Lambda_python3.7 Botocore/1.21.36",
                "requestParameters": {
                    "roleName": "abcrole",
                    "tags": [{"key": "1", "value": "1"}, {"key": "2", "value": "2"}],
                },
                "responseElements": None,
                "requestID": "11111-f97e-413d-ba51-299816b1bd0d",
                "eventID": "111111-436a-45ee-b0f2-5ea9e155dd56",
                "readOnly": False,
                "eventType": "AwsApiCall",
                "managementEvent": True,
                "recipientAccountId": "123456789012",
                "eventCategory": "Management",
            },
        }
    )
    sqs.send_message(QueueUrl=queue_url["QueueUrl"], MessageBody=message)

    queue_url = sqs.get_queue_url(
        QueueName="consoleme-cloudtrail-access-deny-events-test"
    )
    message = json.dumps(
        {
            "Message": json.dumps(
                {
                    "version": "0",
                    "id": "12345",
                    "detail-type": "AWS API Call via CloudTrail",
                    "source": "aws.sts",
                    "account": "123456789012",
                    "time": "2021-06-22T16:17:45Z",
                    "region": "us-east-1",
                    "resources": [],
                    "detail": {
                        "eventVersion": "1.08",
                        "userIdentity": {
                            "type": "AssumedRole",
                            "principalId": "principalId",
                            "arn": "arn:aws:sts::123456789012:assumed-role/roleA/instanceId",
                            "accountId": "123456789012",
                            "accessKeyId": "ASIASFT37IGO3U7IQ5RA",
                            "sessionContext": {
                                "sessionIssuer": {
                                    "type": "Role",
                                    "principalId": "principalId",
                                    "arn": "arn:aws:iam::123456789012:role/roleA",
                                    "accountId": "123456789012",
                                    "userName": "roleA",
                                },
                                "webIdFederationData": {},
                                "attributes": {
                                    "creationDate": "2021-06-22T10:59:51Z",
                                    "mfaAuthenticated": "false",
                                },
                                "ec2RoleDelivery": "2.0",
                            },
                        },
                        "eventTime": current_time,
                        "eventSource": "sts.amazonaws.com",
                        "eventName": "AssumeRole",
                        "awsRegion": "global",
                        "sourceIPAddress": "1.2.3.4",
                        "userAgent": "userAgent",
                        "errorCode": "AccessDenied",
                        "errorMessage": "User: arn:aws:sts::123456789012:assumed-role/roleA/instanceId is not authorized to perform: sts:AssumeRole on resource: arn:aws:iam::123456789012:role/roleB",
                        "requestParameters": None,
                        "responseElements": None,
                        "requestID": "404804f0-0b62-4220-8766-0e145cb85be9",
                        "eventID": "cfaf5898-f822-47ce-ba52-1b01aabc18f4",
                        "readOnly": True,
                        "eventType": "AwsApiCall",
                        "managementEvent": True,
                        "recipientAccountId": "123456789012",
                        "eventCategory": "Management",
                        "tlsDetails": {
                            "tlsVersion": "TLSv1.2",
                            "cipherSuite": "ECDHE-RSA-AES128-SHA",
                            "clientProvidedHostHeader": "sts.amazonaws.com",
                        },
                    },
                }
            )
        }
    )
    sqs.send_message(QueueUrl=queue_url["QueueUrl"], MessageBody=message)
    yield sqs


@pytest.fixture(autouse=False, scope="session")
def policy_requests_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="policy_requests_multitenant",
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
                "IndexName": "arn-request_id-index",
                "KeySchema": [{"AttributeName": "arn", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 123,
                    "WriteCapacityUnits": 123,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )

    yield dynamodb


@pytest.fixture(autouse=False, scope="session")
def requests_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="requests_global",
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "request_id", "KeyType": "RANGE"},
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "request_id", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield dynamodb


@pytest.fixture(autouse=False, scope="session")
def users_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="users_multitenant",
        AttributeDefinitions=[
            {"AttributeName": "tenant", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "tenant", "KeyType": "HASH"},
            {"AttributeName": "username", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield dynamodb


@pytest.fixture(autouse=False, scope="session")
def tenant_static_configs_table(dynamodb):
    table_name = "tenant_static_configs"
    dynamodb.create_table(
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
            "StreamEnabled": False,
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

    yield dynamodb


@pytest.fixture(autouse=True, scope="session")
def with_test_configuration_tenant_static_config_data(
    tenant_static_configs_table, tenant_details_table
):
    from common.lib import dynamo
    from common.lib.tenant.models import TenantDetails

    ddb = dynamo.RestrictedDynamoHandler()
    with open("util/tests/test_configuration.yaml", "r") as fp:
        config_dict = async_to_sync(ddb.update_static_config_for_tenant)(
            fp, "test@noq.dev", "test.noq.dev".replace(".", "_")
        )
        tenants = list(config_dict.get("site_configs", {}).keys())
        for tenant_name in tenants:
            async_to_sync(TenantDetails.create)(
                tenant_name, "test_user", eula_info={"signed": True}, noq_cluster="1"
            )


@pytest.fixture(autouse=False, scope="session")
def dummy_requests_data(requests_table):
    user = {
        "tenant": {"S": tenant},
        "request_id": {"S": "abc-def-ghi"},
        "aws:rep:deleting": {"BOOL": False},
        "aws:rep:updateregion": {"S": "us-west-2"},
        "aws:rep:updatetime": {"N": "1547848006"},
        "group": {"S": "test_group"},
        "justification": {"S": "some reason"},
        "last_updated": {"N": "1245678901"},
        "request_time": {"N": "1234567890"},
        "status": {"S": "pending"},
        "updated_by": {"S": "somebody@somewhere.org"},
        "username": {"S": "test@user.xyz"},
        "reviewer_commnets": {"S": "All the access!"},
    }
    from common.lib.dynamo import BaseDynamoHandler

    requests_table.put_item(
        TableName="requests_global",
        Item=BaseDynamoHandler()._data_to_dynamo_replace(user),
    )

    yield requests_table


@pytest.fixture(autouse=False, scope="session")
def dummy_users_data(users_table):
    user = {
        "tenant": {"S": tenant},
        "username": {"S": "test@user.xyz"},
        "aws:rep:deleting": {"BOOL": False},
        "aws:rep:updateregion": {"S": "us-west-2"},
        "last_udpated": {"N": "1547848006"},
        "requests": {"L": [{"S": "abc-def-ghi"}]},
    }
    from common.lib.dynamo import BaseDynamoHandler

    users_table.put_item(
        TableName="users_multitenant",
        Item=BaseDynamoHandler()._data_to_dynamo_replace(user),
    )

    yield users_table


@pytest.fixture(autouse=False, scope="session")
def iam_sync_principals(iam):
    statement_policy = json.dumps(
        {
            "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
            "Version": "2012-10-17",
        }
    )

    assume_role_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:role/ConsoleMeInstanceProfile"
                    },
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )

    # Create the role that CloudAux will assume:
    iam.create_role(RoleName="ConsoleMe", AssumeRolePolicyDocument=assume_role_policy)
    # Create a generic test instance profile
    iam.create_role(
        RoleName="TestInstanceProfile", AssumeRolePolicyDocument=assume_role_policy
    )

    # Create a managed policy:
    policy_one = iam.create_policy(
        PolicyName="policy-one", PolicyDocument=statement_policy
    )["Policy"]["Arn"]
    policy_two = iam.create_policy(
        PolicyName="policy-two", PolicyDocument=statement_policy
    )["Policy"]["Arn"]

    iam.create_user(UserName="TestUser")
    iam.put_user_policy(
        UserName="TestUser",
        PolicyName="SomePolicy",
        PolicyDocument=statement_policy,
    )

    iam.attach_user_policy(UserName="TestUser", PolicyArn=policy_one)

    # Create 50 IAM roles for syncing:
    for x in range(0, 10):
        iam.create_role(
            RoleName=f"RoleNumber{x}", AssumeRolePolicyDocument=assume_role_policy
        )
        iam.put_role_policy(
            RoleName=f"RoleNumber{x}",
            PolicyName="SomePolicy",
            PolicyDocument=statement_policy,
        )
        iam.tag_role(
            RoleName=f"RoleNumber{x}",
            Tags=[
                {"Key": "Number", "Value": f"{x}"},
                {"Key": "authorized_groups", "Value": f"group{x}:group{x}@example.com"},
                {
                    "Key": "authorized_groups_cli_only",
                    "Value": f"group{x}-cli:group{x}-cli@example.com",
                },
            ],
        )
        iam.attach_role_policy(RoleName=f"RoleNumber{x}", PolicyArn=policy_one)
        iam.attach_role_policy(RoleName=f"RoleNumber{x}", PolicyArn=policy_two)

    # Create the dynamic user role:
    iam.create_role(
        RoleName="awsaccount_user", AssumeRolePolicyDocument=assume_role_policy
    )
    iam.put_role_policy(
        RoleName="awsaccount_user",
        PolicyName="SomePolicy",
        PolicyDocument=statement_policy,
    )
    iam.attach_role_policy(RoleName="awsaccount_user", PolicyArn=policy_one)

    # Create another dynamic user role

    iam.create_role(
        RoleName="cm_someuser_N", AssumeRolePolicyDocument=assume_role_policy
    )
    iam.put_role_policy(
        RoleName="cm_someuser_N",
        PolicyName="SomePolicy",
        PolicyDocument=statement_policy,
    )
    iam.attach_role_policy(RoleName="cm_someuser_N", PolicyArn=policy_one)

    iam.create_role(RoleName="rolename", AssumeRolePolicyDocument=assume_role_policy)
    iam.attach_role_policy(RoleName="rolename", PolicyArn=policy_one)

    yield iam


@pytest.fixture(autouse=False, scope="session")
def www_user():
    return json.loads(
        """{
        "Path": "/",
        "RoleName": "rolename",
        "RoleId": "AROAI5FHPGAEE6FRM5Q2Y",
        "Arn": "arn:aws:iam::123456789012:role/rolename",
        "CreateDate": "2017-10-06T22:07:23Z",
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": "arn:aws:iam::123456789012:saml-provider/saml"
                    },
                    "Action": "sts:AssumeRoleWithSAML",
                    "Condition": {
                        "StringEquals": {
                            "SAML:aud": "https://signin.aws.amazon.com/saml"
                        }
                    }
                },
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:role/consoleme"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        },
        "InstanceProfileList": [],
        "RolePolicyList": [
            {
                "PolicyName": "user",
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "ec2:Describe*",
                                "lambda:Describe*",
                                "sns:List*",
                                "sqs:List*"
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "*"
                            ]
                        },
                        {
                            "Action": [
                                "iam:List*"
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "*"
                            ]
                        }
                    ],
                    "Version": "2012-10-17"
                }
            }
        ],
        "AttachedManagedPolicies": [
            {
                "PolicyName": "Abc",
                "PolicyArn": "arn:aws:iam::123456789012:policy/Abc"
            },
            {
                "PolicyName": "Encrypt",
                "PolicyArn": "arn:aws:iam::123456789012:policy/Encrypt"
            },
            {
                "PolicyName": "ReadOnlyAccess",
                "PolicyArn": "arn:aws:iam::aws:policy/ReadOnlyAccess"
            },
            {
                "PolicyName": "Tag",
                "PolicyArn": "arn:aws:iam::123456789012:policy/Tag"
            }
        ],
        "Tags": []
    }"""
    )


fakeredis_server = fakeredis.FakeServer()

fake_redis = fakeredis.FakeRedis(server=fakeredis_server, decode_responses=True)

fake_strict_redis = fakeredis.FakeStrictRedis(
    server=fakeredis_server, decode_responses=True
)

# class FakeRedis(fakeredis.FakeStrictRedis):
#     def __init__(self, *args, **kwargs):
#         super(FakeRedis, self).__init__(*args, **kwargs, server=fakeredis_server, connection_pool=None)


@pytest.fixture(autouse=False, scope="session")
def redis(session_mocker):
    from common.config import config

    if folder_configuration := config.get("_global_.celery.broker_transport_options"):
        for v in folder_configuration.values():
            os.makedirs(v, exist_ok=True)
    session_mocker.patch("celery.backends.redis.redis.Redis", return_value=fake_redis)
    session_mocker.patch("redis.Redis", return_value=fake_redis)
    session_mocker.patch("redis.StrictRedis", return_value=fake_strict_redis)
    session_mocker.patch(
        "common.lib.redis.redis.StrictRedis", return_value=fake_strict_redis
    )
    session_mocker.patch("common.lib.redis.redis.Redis", return_value=fake_redis)
    session_mocker.patch(
        "common.lib.redis.RedisHandler.redis_sync", return_value=fake_redis
    )
    session_mocker.patch("common.lib.redis.RedisHandler.redis", return_value=fake_redis)
    return True


class MockParliament:
    def __init__(self, return_value=None):
        self.return_value = return_value

    @property
    def findings(self):
        return self.return_value


class Finding:
    issue = ""
    detail = ""
    location = {}
    severity = ""
    title = ""
    description = ""

    def __init__(
        self,
        issue,
        detail,
        location,
        severity,
        title,
        description,
    ):
        self.issue = issue
        self.detail = detail
        self.location = location
        self.severity = severity
        self.title = title
        self.description = description


@pytest.fixture(scope="session")
def parliament(session_mocker):
    session_mocker.patch(
        "parliament.analyze_policy_string",
        return_value=MockParliament(
            return_value=[
                {
                    "issue": "RESOURCE_MISMATCH",
                    "title": "No resources match for the given action",
                    "severity": "MEDIUM",
                    "description": "",
                    "detail": [
                        {"action": "s3:GetObject", "required_format": "arn:*:s3:::*/*"}
                    ],
                    "location": {"line": 3, "column": 18, "filepath": "test.json"},
                }
            ]
        ),
    )

    session_mocker.patch(
        "parliament.enhance_finding",
        return_value=Finding(
            issue="RESOURCE_MISMATCH",
            title="No resources match for the given action",
            severity="MEDIUM",
            description="",
            detail="",
            location={},
        ),
    )


@pytest.fixture(scope="session")
def user_iam_role(iamrole_table, www_user):
    from common.aws.iam.role.models import IAMRole

    role_entry = IAMRole(
        arn=www_user.get("Arn"),
        name=www_user.get("RoleName"),
        accountId="123456789012",
        policy=IAMRole().dump_json_attr(www_user),
        tenant=tenant,
        entity_id=f"{www_user.get('Arn')}||{tenant}",
        last_updated=int((datetime.utcnow()).timestamp()),
        resourceId=www_user.get("RoleId"),
    )
    async_to_sync(role_entry.save)()


@pytest.fixture(autouse=False, scope="session")
def mock_exception_stats():
    p = patch("common.exceptions.exceptions.get_plugin_by_name")

    yield p.start()

    p.stop()


@pytest.fixture(autouse=False, scope="session")
def mock_celery_stats(mock_exception_stats):
    p = patch("common.celery_tasks.celery_tasks.stats")

    yield p.start()

    p.stop()


@pytest.fixture(scope="session")
def mock_async_http_client():
    p_return_value = Mock()
    p_return_value.body = "{}"
    p = patch("tornado.httpclient.AsyncHTTPClient")

    p.return_value.fetch.return_value = p_return_value

    yield p.start()

    p.stop()


@pytest.fixture(autouse=False, scope="session")
def populate_caches(
    redis,
    user_iam_role,
    iam_sync_principals,
    dummy_users_data,
    dummy_requests_data,
    policy_requests_table,
    iamrole_table,
    create_default_resources,
    s3,
    sns,
    sqs,
    iam,
    www_user,
    parliament,
    ec2,
):
    from asgiref.sync import async_to_sync

    from common.celery_tasks import celery_tasks as celery
    from common.lib.account_indexers import get_account_id_to_name_mapping

    celery.cache_cloud_account_mapping(tenant)
    accounts_d = async_to_sync(get_account_id_to_name_mapping)(tenant)

    for account_id in accounts_d.keys():
        celery.cache_iam_resources_for_account(account_id, tenant=tenant)
        celery.cache_s3_buckets_for_account(account_id, tenant=tenant)
        celery.cache_sns_topics_for_account(account_id, tenant=tenant)
        celery.cache_sqs_queues_for_account(account_id, tenant=tenant)
        celery.cache_managed_policies_for_account(account_id, tenant=tenant)
        # celery.cache_resources_from_aws_config_for_account(account_id) # No select_resource_config in moto yet
    # Running cache_iam_resources_across_accounts ensures that all of the pre-existing roles in our
    # role cache are stored in (mock) S3
    celery.cache_iam_resources_across_accounts(
        tenant=tenant, wait_for_subtask_completion=False
    )
    celery.cache_policies_table_details(tenant=tenant)
    celery.cache_credential_authorization_mapping(tenant=tenant)


class MockAioHttpResponse:
    status = 200
    responses = []

    @classmethod
    async def json(cls):
        try:
            return cls.responses.pop(0)
        except Exception:  # noqa
            return []


class MockAioHttpRequest:
    @classmethod
    async def get(cls, *args, **kwargs):
        return MockAioHttpResponse()

    @classmethod
    async def post(cls, *args, **kwargs):
        return MockAioHttpResponse()


def create_future(ret_val=None):
    future = Future()
    future.set_result(ret_val)
    return future
