import asyncio
import copy
import time
from datetime import datetime, timedelta
from unittest import TestCase

import boto3
import pytest
import pytz
import ujson as json
from asgiref.sync import async_to_sync
from mock import patch

from common.models import (
    ChangeModelArray,
    ExtendedRequestModel,
    InlinePolicyChangeModel,
    RequestStatus,
    Status,
    UserModel,
)
from util.tests.fixtures.fixtures import create_future
from util.tests.fixtures.globals import host

ROLE = {
    "Arn": "arn:aws:iam::123456789012:role/TestInstanceProfile",
    "RoleName": "TestInstanceProfile",
    "CreateDate": datetime.now(tz=pytz.utc) - timedelta(days=5),
    "AttachedManagedPolicies": [{"PolicyName": "Policy1"}, {"PolicyName": "Policy2"}],
    "Tags": [{"Key": "tag1", "Value": "value1"}],
}


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("sts")
class TestAwsLib(TestCase):
    def test_is_role_instance_profile(self):
        from common.lib.aws.utils import is_role_instance_profile

        self.assertTrue(is_role_instance_profile(ROLE))

    def test_is_role_instance_profile_false(self):
        from common.lib.aws.utils import is_role_instance_profile

        role = {"RoleName": "Test"}
        self.assertFalse(is_role_instance_profile(role))

    def test_role_newer_than_x_days(self):
        from common.lib.aws.utils import role_newer_than_x_days

        self.assertTrue(role_newer_than_x_days(ROLE, 30))

    def test_role_newer_than_x_days_false(self):
        from common.lib.aws.utils import role_newer_than_x_days

        self.assertFalse(role_newer_than_x_days(ROLE, 1))

    def test_role_has_managed_policy(self):
        from common.lib.aws.utils import role_has_managed_policy

        self.assertTrue(role_has_managed_policy(ROLE, "Policy1"))

    def test_role_has_managed_policy_false(self):
        from common.lib.aws.utils import role_has_managed_policy

        self.assertFalse(role_has_managed_policy(ROLE, "Policy3"))

    def test_role_has_tag(self):
        from common.lib.aws.utils import role_has_tag

        self.assertTrue(role_has_tag(ROLE, "tag1"))
        self.assertTrue(role_has_tag(ROLE, "tag1", "value1"))

    def test_role_has_tag_false(self):
        from common.lib.aws.utils import role_has_tag

        self.assertFalse(role_has_tag(ROLE, "tag2"))
        self.assertFalse(role_has_tag(ROLE, "tag2", "value1"))
        self.assertFalse(role_has_tag(ROLE, "tag1", "value2"))

    def test_apply_managed_policy_to_role(self):
        from common.lib.aws.utils import apply_managed_policy_to_role

        apply_managed_policy_to_role(ROLE, "policy-one", "session", host)

    @patch("common.lib.aws.utils.redis_hget")
    def test_get_resource_account(self, mock_aws_config_resources_redis):
        from common.lib.aws.utils import get_resource_account

        mock_aws_config_resources_redis.return_value = create_future(None)
        test_cases = [
            {
                "arn": "arn:aws:s3:::nope",
                "expected": "",
                "description": "external S3 bucket",
            },
            {
                "arn": "arn:aws:waddup:us-east-1:987654321000:cool-resource",
                "expected": "987654321000",
                "description": "arbitrary resource with account in ARN",
            },
            {
                "arn": "arn:aws:waddup:us-east-1::cool-resource",
                "expected": "",
                "description": "arbitrary resource without account in ARN",
            },
        ]
        loop = asyncio.get_event_loop()
        for tc in test_cases:
            result = loop.run_until_complete(get_resource_account(tc["arn"], host))
            self.assertEqual(
                tc["expected"], result, f"Test case failed: {tc['description']}"
            )

        aws_config_resources_test_case = {
            "arn": "arn:aws:s3:::foobar",
            "expected": "123456789012",
            "description": "internal S3 bucket",
        }
        aws_config_resources_test_case_redis_result = {"accountId": "123456789012"}
        mock_aws_config_resources_redis.return_value = create_future(
            json.dumps(aws_config_resources_test_case_redis_result)
        )
        result = loop.run_until_complete(
            get_resource_account(aws_config_resources_test_case["arn"], host)
        )
        self.assertEqual(
            aws_config_resources_test_case["expected"],
            result,
            f"Test case failed: " f"{aws_config_resources_test_case['description']}",
        )

    def test_is_member_of_ou(self):
        from common.lib.aws.utils import _is_member_of_ou

        loop = asyncio.get_event_loop()
        fake_org = {
            "Id": "r",
            "Children": [
                {
                    "Id": "a",
                    "Type": "ORGANIZATIONAL_UNIT",
                    "Children": [
                        {
                            "Id": "b",
                            "Type": "ORGANIZATIONAL_UNIT",
                            "Children": [{"Id": "100", "Type": "ACCOUNT"}],
                        }
                    ],
                },
            ],
        }

        # Account ID in nested OU
        result, ous = loop.run_until_complete(_is_member_of_ou("100", fake_org))
        self.assertTrue(result)
        self.assertEqual(ous, {"b", "a", "r"})

        # OU ID in OU structure
        result, ous = loop.run_until_complete(_is_member_of_ou("b", fake_org))
        self.assertTrue(result)
        self.assertEqual(ous, {"a", "r"})

        # ID not in OU structure
        result, ous = loop.run_until_complete(_is_member_of_ou("101", fake_org))
        self.assertFalse(result)
        self.assertEqual(ous, set())

    def test_scp_targets_account_or_ou(self):
        from common.lib.aws.utils import _scp_targets_account_or_ou
        from common.models import (
            ServiceControlPolicyDetailsModel,
            ServiceControlPolicyModel,
            ServiceControlPolicyTargetModel,
        )

        loop = asyncio.get_event_loop()
        blank_scp_details = ServiceControlPolicyDetailsModel(
            id="",
            arn="",
            name="",
            description="",
            aws_managed=False,
            content="",
        )

        # SCP targets account directly
        scp_targets = [
            ServiceControlPolicyTargetModel(
                target_id="100", arn="", name="", type="ACCOUNT"
            )
        ]
        fake_scp = ServiceControlPolicyModel(
            targets=scp_targets, policy=blank_scp_details
        )
        fake_ous = set()
        result = loop.run_until_complete(
            _scp_targets_account_or_ou(fake_scp, "100", fake_ous)
        )
        self.assertTrue(result)

        # SCP targets OU of which account is a member
        scp_targets = [
            ServiceControlPolicyTargetModel(
                target_id="abc123", arn="", name="", type="ORGANIZATIONAL_UNIT"
            )
        ]
        fake_scp = ServiceControlPolicyModel(
            targets=scp_targets, policy=blank_scp_details
        )
        fake_ous = {"abc123", "def456"}
        result = loop.run_until_complete(
            _scp_targets_account_or_ou(fake_scp, "100", fake_ous)
        )
        self.assertTrue(result)

        # SCP doesn't target account
        scp_targets = [
            ServiceControlPolicyTargetModel(
                target_id="ghi789", arn="", name="", type="ORGANIZATIONAL_UNIT"
            )
        ]
        fake_scp = ServiceControlPolicyModel(
            targets=scp_targets, policy=blank_scp_details
        )
        fake_ous = {"abc123", "def456"}
        result = loop.run_until_complete(
            _scp_targets_account_or_ou(fake_scp, "100", fake_ous)
        )
        self.assertFalse(result)

    def test_fetch_managed_policy_details(self):
        from common.config import config
        from common.lib.aws.utils import fetch_managed_policy_details

        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            fetch_managed_policy_details("123456789012", "policy-one", host)
        )
        self.assertDictEqual(
            result["Policy"],
            {
                "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
                "Version": "2012-10-17",
            },
        )
        self.assertListEqual(result["TagSet"], [])

        with pytest.raises(Exception) as e:
            loop.run_until_complete(
                fetch_managed_policy_details(
                    "123456789012", "policy-non-existent", host
                )
            )

        self.assertIn("NoSuchEntity", str(e))

        # test paths
        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_host_specific_key("boto3.client_kwargs", host, {}),
        )
        policy_name = "policy_with_paths"
        policy_path = "/testpath/testpath2/"
        client.create_policy(
            PolicyName=policy_name,
            Path=policy_path,
            PolicyDocument=json.dumps(result["Policy"]),
        )
        result = loop.run_until_complete(
            fetch_managed_policy_details(
                "123456789012", policy_name, host, path="testpath/testpath2"
            )
        )
        self.assertDictEqual(
            result["Policy"],
            {
                "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
                "Version": "2012-10-17",
            },
        )

    def test_allowed_to_sync_role(self):
        from common.config.config import CONFIG
        from common.lib.aws.utils import allowed_to_sync_role

        old_config = copy.deepcopy(CONFIG.config)
        test_role_arn = "arn:aws:iam::111111111111:role/role-name-here-1"
        test_role_tags = [
            {"Key": "testtag", "Value": "testtagv"},
            {"Key": "testtag2", "Value": "testtag2v"},
        ]

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, host), True
        )

        # Allow - allowed_tags exists in role
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                host: {
                    "roles": {
                        "allowed_tags": {"testtag": "testtagv"},
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, host), True
        )

        # Reject, one of the tags doesn't exist on role
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                host: {
                    "roles": {
                        "allowed_tags": {
                            "testtag": "testtagv",
                            "testtagNOTEXIST": "testv",
                        },
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, host), False
        )

        # Allow - Role has all allowed_tags, doesn't matter that allowed_arns doesn't have our role ARN
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                host: {
                    "roles": {
                        "allowed_tags": {"testtag": "testtagv"},
                        "allowed_arns": [
                            "arn:aws:iam::111111111111:role/some-other-role"
                        ],
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, host), True
        )

        # Allow - Role has all allowed_tags
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                host: {
                    "roles": {
                        "allowed_tags": {"testtag": "testtagv"},
                        "allowed_arns": ["arn:aws:iam::111111111111:role/BADROLENAME"],
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, host), True
        )

        # Reject - No tag
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                host: {
                    "roles": {
                        "allowed_tags": {"a": "b"},
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, host), False
        )

        # Allow by ARN
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                host: {
                    "roles": {
                        "allowed_arns": [
                            "arn:aws:iam::111111111111:role/role-name-here-1"
                        ]
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, host), True
        )

        CONFIG.config = old_config

    @pytest.mark.usefixtures("dynamodb")
    @patch("common.lib.dynamo.UserDynamoHandler.write_policy_request_v2")
    @patch("common.lib.aws.fetch_iam_principal.fetch_iam_role")
    def test_remove_temp_policies(self, mock_dynamo_write, mock_fetch_iam_role):
        from common.lib.aws.utils import remove_temp_policies

        mock_dynamo_write.return_value = create_future(None)
        mock_fetch_iam_role.return_value = create_future(None)

        account_id = "123456789012"
        current_dateint = datetime.today().strftime("%Y%m%d")
        past_dateint = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        future_dateint = (datetime.today() + timedelta(days=1)).strftime("%Y%m%d")

        test_role_name = "TestRequestsLibV2RoleName"
        policy_name = "test_inline_policy_change"
        test_role_arn = f"arn:aws:iam::{account_id}:role/{test_role_name}"

        inline_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "applied",
            "policy_name": policy_name,
            "id": "1234_0",
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {},
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
            "expiration_date": current_dateint,
        }
        inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            principal=dict(
                principal_type="AwsResource",
                principal_arn=test_role_arn,
            ),
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[inline_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        # Should be deleted if date is current date
        extended_request.request_status = RequestStatus.approved
        extended_request.expiration_date = current_dateint
        extended_request.changes.changes[0].status = Status.applied
        async_to_sync(remove_temp_policies)(extended_request, host)
        self.assertEqual(extended_request.request_status, RequestStatus.expired)
        self.assertEqual(extended_request.changes.changes[0].status, Status.expired)

        # Should be deleted if date is past date
        extended_request.request_status = RequestStatus.approved
        extended_request.expiration_date = past_dateint
        extended_request.changes.changes[0].status = Status.applied
        async_to_sync(remove_temp_policies)(extended_request, host)
        self.assertEqual(extended_request.request_status, RequestStatus.expired)
        self.assertEqual(extended_request.changes.changes[0].status, Status.expired)

        # Should not be deleted if date is future date
        extended_request.expiration_date = future_dateint
        extended_request.request_status = RequestStatus.approved
        extended_request.changes.changes[0].status = Status.applied
        async_to_sync(remove_temp_policies)(extended_request, host)
        self.assertEqual(extended_request.request_status, RequestStatus.approved)
        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)

        # Should not be deleted if date is invalid date
        extended_request.expiration_date = None
        extended_request.request_status = RequestStatus.approved
        extended_request.changes.changes[0].status = Status.applied
        async_to_sync(remove_temp_policies)(extended_request, host)
        self.assertEqual(extended_request.request_status, RequestStatus.approved)
        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)
