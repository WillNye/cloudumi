import asyncio
import copy
import time
from datetime import datetime, timedelta
from unittest import TestCase

import boto3
import pytest
import pytz
from asgiref.sync import async_to_sync
from mock import patch

import common.lib.noq_json as json
from common.aws.iam.statement.utils import condense_statements
from common.models import (
    ChangeModelArray,
    ExtendedRequestModel,
    InlinePolicyChangeModel,
    RequestStatus,
    Status,
    UserModel,
)
from util.tests.fixtures.globals import tenant

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
    def test_role_has_tag(self):
        from common.aws.utils import get_resource_tag

        self.assertTrue(bool(get_resource_tag(ROLE, "tag1")))
        self.assertEqual(get_resource_tag(ROLE, "tag1"), "value1")

    def test_role_has_tag_false(self):
        from common.aws.utils import get_resource_tag

        self.assertFalse(bool(get_resource_tag(ROLE, "tag2")))
        self.assertNotEqual(get_resource_tag(ROLE, "tag2"), "value1")
        self.assertNotEqual(get_resource_tag(ROLE, "tag1"), "value2")

    @patch("common.lib.aws.utils.redis_hget")
    def test_get_resource_account(self, mock_aws_config_resources_redis):
        from common.aws.utils import get_resource_account

        loop = asyncio.new_event_loop()
        mock_aws_config_resources_redis.return_value = None
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
        for tc in test_cases:
            result = loop.run_until_complete(get_resource_account(tc["arn"], tenant))
            self.assertEqual(
                tc["expected"], result, f"Test case failed: {tc['description']}"
            )

        aws_config_resources_test_case = {
            "arn": "arn:aws:s3:::foobar",
            "expected": "123456789012",
            "description": "internal S3 bucket",
        }
        aws_config_resources_test_case_redis_result = {"accountId": "123456789012"}
        mock_aws_config_resources_redis.return_value = json.dumps(
            aws_config_resources_test_case_redis_result
        )
        result = async_to_sync(get_resource_account)(
            aws_config_resources_test_case["arn"], tenant
        )
        self.assertEqual(
            aws_config_resources_test_case["expected"],
            result,
            f"Test case failed: " f"{aws_config_resources_test_case['description']}",
        )

    def test_is_member_of_ou(self):
        from common.lib.aws.utils import _is_member_of_ou

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
        result, ous = async_to_sync(_is_member_of_ou)("100", fake_org)
        self.assertTrue(result)
        self.assertEqual(ous, {"b", "a", "r"})

        # OU ID in OU structure
        result, ous = async_to_sync(_is_member_of_ou)("b", fake_org)
        self.assertTrue(result)
        self.assertEqual(ous, {"a", "r"})

        # ID not in OU structure
        result, ous = async_to_sync(_is_member_of_ou)("101", fake_org)
        self.assertFalse(result)
        self.assertEqual(ous, set())

    def test_scp_targets_account_or_ou(self):
        from common.lib.aws.utils import _scp_targets_account_or_ou
        from common.models import (
            ServiceControlPolicyDetailsModel,
            ServiceControlPolicyModel,
            ServiceControlPolicyTargetModel,
        )

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
        result = async_to_sync(_scp_targets_account_or_ou)(fake_scp, "100", fake_ous)
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
        result = async_to_sync(_scp_targets_account_or_ou)(fake_scp, "100", fake_ous)
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
        result = async_to_sync(_scp_targets_account_or_ou)(fake_scp, "100", fake_ous)
        self.assertFalse(result)

    def test_fetch_managed_policy_details(self):
        from common.aws.iam.policy.utils import fetch_managed_policy_details
        from common.config import config

        result = async_to_sync(fetch_managed_policy_details)(
            "123456789012", "policy-one", tenant, None
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
            async_to_sync(fetch_managed_policy_details)(
                "123456789012", "policy-non-existent", tenant, None
            )

        self.assertIn("NoSuchEntity", str(e))

        # test paths
        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        policy_name = "policy_with_paths"
        policy_path = "/testpath/testpath2/"
        client.create_policy(
            PolicyName=policy_name,
            Path=policy_path,
            PolicyDocument=json.dumps(result["Policy"]),
        )
        result = async_to_sync(fetch_managed_policy_details)(
            "123456789012", policy_name, tenant, None, path="testpath/testpath2"
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
            allowed_to_sync_role(test_role_arn, test_role_tags, tenant), True
        )

        # Allow - allowed_tags exists in role
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                tenant: {
                    "roles": {
                        "allowed_tags": {"testtag": "testtagv"},
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, tenant), True
        )

        # Reject, one of the tags doesn't exist on role
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                tenant: {
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
            allowed_to_sync_role(test_role_arn, test_role_tags, tenant), False
        )

        # Allow - Role has all allowed_tags, doesn't matter that allowed_arns doesn't have our role ARN
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                tenant: {
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
            allowed_to_sync_role(test_role_arn, test_role_tags, tenant), True
        )

        # Allow - Role has all allowed_tags
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                tenant: {
                    "roles": {
                        "allowed_tags": {"testtag": "testtagv"},
                        "allowed_arns": ["arn:aws:iam::111111111111:role/BADROLENAME"],
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, tenant), True
        )

        # Reject - No tag
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                tenant: {
                    "roles": {
                        "allowed_tags": {"a": "b"},
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, tenant), False
        )

        # Allow by ARN
        CONFIG.config = {
            **CONFIG.config,
            "site_configs": {
                tenant: {
                    "roles": {
                        "allowed_arns": [
                            "arn:aws:iam::111111111111:role/role-name-here-1"
                        ]
                    },
                }
            },
        }

        self.assertEqual(
            allowed_to_sync_role(test_role_arn, test_role_tags, tenant), True
        )

        CONFIG.config = old_config

    @pytest.mark.usefixtures("policy_requests_table")
    @pytest.mark.usefixtures("redis")
    @pytest.mark.usefixtures("iam")
    def test_remove_temp_policies(self):
        from common.lib.aws.utils import remove_expired_tenant_requests
        from common.user_request.models import IAMRequest

        account_id = "123456789012"
        current_dateint = datetime.today().strftime("%Y%m%d")
        past_dateint = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        future_dateint = (datetime.today() + timedelta(days=5)).strftime("%Y%m%d")

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
        async_to_sync(IAMRequest.write_v2)(extended_request, tenant)
        async_to_sync(remove_expired_tenant_requests)(tenant)
        iam_request = async_to_sync(IAMRequest.get)(
            tenant, request_id=extended_request.id
        )
        extended_request = ExtendedRequestModel.parse_obj(
            iam_request.extended_request.dict()
        )
        self.assertEqual(extended_request.request_status, RequestStatus.expired)
        self.assertEqual(extended_request.changes.changes[0].status, Status.expired)

        # Should be deleted if date is past date
        extended_request.request_status = RequestStatus.approved
        extended_request.expiration_date = past_dateint
        extended_request.changes.changes[0].status = Status.applied
        async_to_sync(IAMRequest.write_v2)(extended_request, tenant)
        async_to_sync(remove_expired_tenant_requests)(tenant)
        # Refresh the request
        iam_request = async_to_sync(IAMRequest.get)(
            tenant, request_id=extended_request.id
        )
        extended_request = ExtendedRequestModel.parse_obj(
            iam_request.extended_request.dict()
        )
        self.assertEqual(extended_request.request_status, RequestStatus.expired)
        self.assertEqual(extended_request.changes.changes[0].status, Status.expired)

        # Should not be deleted if date is future date
        extended_request.expiration_date = future_dateint
        extended_request.request_status = RequestStatus.approved
        extended_request.changes.changes[0].status = Status.applied
        async_to_sync(IAMRequest.write_v2)(extended_request, tenant)
        async_to_sync(remove_expired_tenant_requests)(tenant)
        # Refresh the request
        iam_request = async_to_sync(IAMRequest.get)(
            tenant, request_id=extended_request.id
        )
        extended_request = ExtendedRequestModel.parse_obj(
            iam_request.extended_request.dict()
        )
        self.assertEqual(extended_request.request_status, RequestStatus.approved)
        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)

        # Should not be deleted if date is invalid date
        extended_request.expiration_date = None
        extended_request.request_status = RequestStatus.approved
        extended_request.changes.changes[0].status = Status.applied
        async_to_sync(IAMRequest.write_v2)(extended_request, tenant)
        async_to_sync(remove_expired_tenant_requests)(tenant)
        # Refresh the request
        iam_request = async_to_sync(IAMRequest.get)(
            tenant, request_id=extended_request.id
        )
        extended_request = ExtendedRequestModel.parse_obj(
            iam_request.extended_request.dict()
        )
        self.assertEqual(extended_request.request_status, RequestStatus.approved)
        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)


class TestAwsPolicyNormalizer(TestCase):
    @staticmethod
    def _get_statement_by_resource(policy: list[dict], resource: list[str]) -> dict:
        resource.sort()
        for statement in policy:
            if statement["Resource"] == resource:
                return statement

        return dict()

    def test_reduce_actions(self):
        init_policy = [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem",
                    "dynamodb:Get*",
                    "dynamodb:PutItem",
                    "dynamodb:Query",
                    "dynamodb:UpdateItem",
                ],
                "Resource": ["arn:aws:dynamodb:*:*:table/MyTable"],
                "Condition": {
                    "ForAllValues:StringEquals": {
                        "dynamodb:LeadingKeys": [
                            "${cognito-identity.amazonaws.com:sub}"
                        ]
                    }
                },
            }
        ]

        normalized_policy = async_to_sync(condense_statements)(init_policy)

        # Confirm GetItem was dropped because it's captured under Get* and all other actions remain
        self.assertListEqual(
            normalized_policy[0]["Action"],
            [
                "dynamodb:DeleteItem".lower(),
                "dynamodb:Get*".lower(),
                "dynamodb:PutItem".lower(),
                "dynamodb:Query".lower(),
                "dynamodb:UpdateItem".lower(),
            ],
        )

    def test_group_identical_resources(self):
        init_policy = [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:DeleteItem",
                    "dynamodb:Get*",
                ],
                "Resource": ["arn:aws:dynamodb:*:*:table/MyTable"],
            },
            {
                "Effect": "Allow",
                "Action": ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:UpdateItem"],
                "Resource": ["arn:aws:dynamodb:*:*:table/MyTable"],
            },
        ]

        normalized_policy = async_to_sync(condense_statements)(init_policy)
        self.assertEqual(len(normalized_policy), 1)

        self.assertListEqual(
            normalized_policy[0]["Action"],
            [
                "dynamodb:DeleteItem".lower(),
                "dynamodb:Get*".lower(),
                "dynamodb:PutItem".lower(),
                "dynamodb:Query".lower(),
                "dynamodb:UpdateItem".lower(),
            ],
        )

    def test_remove_identical_actions_from_child_statement(self):
        init_policy = [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:Query",
                    "dynamodb:UpdateItem",
                ],
                "Resource": ["arn:aws:dynamodb:*:*:table/MyTable"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:Get*".lower(),
                    "dynamodb:Query",
                ],
                "Resource": ["arn:aws:dynamodb:*:*"],
            },
        ]

        normalized_policy = async_to_sync(condense_statements)(init_policy)
        self.assertEqual(len(normalized_policy), 2)

        dynamo_statement = self._get_statement_by_resource(
            normalized_policy, ["arn:aws:dynamodb:*:*:table/MyTable"]
        )
        self.assertListEqual(
            dynamo_statement["Action"],
            [
                "dynamodb:DeleteItem".lower(),
                "dynamodb:PutItem".lower(),
                "dynamodb:UpdateItem".lower(),
            ],
        )

    def test_remove_statements_with_no_action(self):
        init_policy = [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:Query",
                    "dynamodb:UpdateItem",
                ],
                "Resource": ["arn:aws:dynamodb:*:*:table/MyTable"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:*",
                ],
                "Resource": ["arn:aws:dynamodb:*:*"],
            },
        ]

        normalized_policy = async_to_sync(condense_statements)(init_policy)
        self.assertEqual(len(normalized_policy), 1)

        dynamo_statement = normalized_policy[0]
        self.assertListEqual(dynamo_statement["Action"], ["dynamodb:*"])
        self.assertListEqual(dynamo_statement["Resource"], ["arn:aws:dynamodb:*:*"])

    def test_dont_reduce_conditionals(self):
        init_policy = [
            {
                "Effect": "Allow",
                "Condition": {
                    "ForAllValues:StringEquals": {
                        "dynamodb:LeadingKeys": [
                            "${cognito-identity.amazonaws.com:sub}"
                        ]
                    }
                },
                "Action": [
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:Query",
                    "dynamodb:UpdateItem",
                ],
                "Resource": ["arn:aws:dynamodb:*:*:table/MyTable"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:Get*".lower(),
                    "dynamodb:Query",
                ],
                "Resource": ["arn:aws:dynamodb:*:*"],
            },
        ]

        normalized_policy = async_to_sync(condense_statements)(init_policy)
        self.assertEqual(len(normalized_policy), 2)

        dynamo_statement = self._get_statement_by_resource(
            normalized_policy, ["arn:aws:dynamodb:*:*:table/MyTable"]
        )
        self.assertListEqual(
            dynamo_statement.get("Action", []),
            [
                "dynamodb:DeleteItem".lower(),
                "dynamodb:GetItem".lower(),
                "dynamodb:PutItem".lower(),
                "dynamodb:Query".lower(),
                "dynamodb:UpdateItem".lower(),
            ],
        )
