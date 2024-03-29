import time
import unittest
from random import randint

import boto3
import pytest
from cachetools import TTLCache
from mock import patch
from pydantic import ValidationError

import common.lib.noq_json as json
from common.lib.assume_role import boto3_cached_conn
from common.lib.v2.requests import is_request_eligible_for_auto_approval
from common.models import (
    Action,
    AssumeRolePolicyChangeModel,
    AwsResourcePrincipalModel,
    ChangeModelArray,
    Command,
    ExtendedAwsPrincipalModel,
    ExtendedRequestModel,
    InlinePolicyChangeModel,
    ManagedPolicyChangeModel,
    ManagedPolicyResourceChangeModel,
    PermissionsBoundaryChangeModel,
    PolicyRequestModificationRequestModel,
    PolicyRequestModificationResponseModel,
    RequestCreationResponse,
    RequestStatus,
    ResourcePolicyChangeModel,
    ResourceTagChangeModel,
    Status,
    TagAction,
    TraRoleChangeModel,
    UserModel,
)
from common.user_request.utils import TRA_CONFIG_BASE_KEY, get_tra_config_for_request
from util.tests.fixtures.globals import role_arn, role_name, tenant

test_role_name = "TestRequestsLibV2RoleName"
test_role_arn = f"arn:aws:iam::123456789012:role/{test_role_name}"

existing_policy_name = "test_inline_policy_change5"
existing_policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "s3:ListBucket",
                "s3:ListBucketVersions",
                "s3:GetObject",
                "s3:GetObjectTagging",
                "s3:GetObjectVersion",
                "s3:GetObjectVersionTagging",
                "s3:GetObjectAcl",
                "s3:GetObjectVersionAcl",
            ],
            "Effect": "Allow",
            "Resource": ["arn:aws:s3:::test_bucket", "arn:aws:s3:::test_bucket/abc/*"],
            "Sid": "sid_test",
        }
    ],
}


async def get_extended_request_helper():
    inline_policy_change = {
        "principal": {
            "principal_arn": test_role_arn,
            "principal_type": "AwsResource",
        },
        "change_type": "inline_policy",
        "resources": [],
        "version": 2.0,
        "status": "not_applied",
        "policy_name": "test_inline_policy_change",
        "id": "1234_0",
        "new": False,
        "action": "attach",
        "policy": {
            "version": None,
            "policy_document": {},
            "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
        },
        "old_policy": None,
    }
    inline_policy_change_model = InlinePolicyChangeModel.parse_obj(inline_policy_change)

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
    return extended_request


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("sts")
@pytest.mark.usefixtures("iam")
class TestRequestsLibV2(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.maxDiff = None
        from botocore.exceptions import ClientError

        from common.config import config

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        role_name = test_role_name
        try:
            client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        except ClientError as e:
            if (
                str(e)
                != "An error occurred (EntityAlreadyExists) when calling the CreateRole operation: Role with name TestRequestsLibV2RoleName already exists."
            ):
                raise

    async def asyncTearDown(self):
        role_name = test_role_name
        from common.aws.iam.role.utils import _delete_iam_role

        await _delete_iam_role("123456789012", role_name, "consoleme-unit-test", tenant)

    async def test_validate_inline_policy_change(self):
        from common.exceptions.exceptions import InvalidRequestParameter
        from common.lib.v2.requests import validate_inline_policy_change

        role = ExtendedAwsPrincipalModel(
            name="role_name",
            account_id="123456789012",
            account_name="friendly_name",
            arn=test_role_arn,
            inline_policies=[],
            assume_role_policy_document={},
            managed_policies=[],
            tags=[],
        )

        inline_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                            ],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        # Attaching a new policy while claiming it's not new
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                "Inline policy not seen but request claims change is not new", str(e)
            )

        # Trying to detach a new policy
        inline_policy_change_model.new = True
        inline_policy_change_model.action = Action.detach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Can't detach an inline policy that is new.", str(e))

        # Trying to detach a non-existent policy
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.detach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Can't detach an inline policy that is not attached.", str(e))

        # Trying to attach a "new" policy that has the same name as an old policy -> Prevent accidental overwrites
        inline_policy_change_model.new = True
        inline_policy_change_model.action = Action.attach
        role.inline_policies = [{"PolicyName": inline_policy_change_model.policy_name}]
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Inline Policy with that name already exists.", str(e))

        # Trying to update an inline policy... without making any changes
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.attach
        role.inline_policies = [
            {
                "PolicyName": inline_policy_change_model.policy_name,
                "PolicyDocument": inline_policy_change_model.policy.policy_document,
            }
        ]
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                "No changes were found between the updated and existing policy.", str(e)
            )

        # Trying to update an inline policy with invalid characters
        inline_policy_change_model.action = Action.attach
        inline_policy_change_model.policy_name = "<>test_invalid_name"
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Invalid characters were detected in the policy.", str(e))

        # Now some tests that should pass validation

        # Updating an inline policy that exists
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.attach
        inline_policy_change_model.policy_name = "test_inline_policy_change"
        role.inline_policies = [
            {"PolicyName": inline_policy_change_model.policy_name, "PolicyDocument": {}}
        ]
        await validate_inline_policy_change(
            inline_policy_change_model, "user@example.com", role
        )

        # Detaching an inline policy
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.detach
        await validate_inline_policy_change(
            inline_policy_change_model, "user@example.com", role
        )

        # Adding a new inline policy
        inline_policy_change_model.new = True
        inline_policy_change_model.action = Action.attach
        inline_policy_change_model.policy_name = "test_inline_policy_change_2"
        await validate_inline_policy_change(
            inline_policy_change_model, "user@example.com", role
        )

    async def test_validate_managed_policy_change(self):
        from common.exceptions.exceptions import InvalidRequestParameter
        from common.lib.v2.requests import validate_managed_policy_change

        role = ExtendedAwsPrincipalModel(
            name="role_name",
            account_id="123456789012",
            account_name="friendly_name",
            arn=test_role_arn,
            inline_policies=[],
            assume_role_policy_document={},
            managed_policies=[],
            tags=[],
        )
        managed_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "managed_policy",
            "policy_name": "invalid<html>characters",
            "resources": [],
            "status": "not_applied",
            "action": "detach",
            "arn": "arn:aws:iam::123456789012:policy/TestManagedPolicy",
        }
        managed_policy_change_model = ManagedPolicyChangeModel.parse_obj(
            managed_policy_change
        )

        # Trying to update an managed policy with invalid characters
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_change(
                managed_policy_change_model, "user@example.com", role
            )
            self.assertIn("Invalid characters were detected in the policy.", str(e))

        # Trying to detach a policy that is not attached
        managed_policy_change_model.action = Action.detach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_change(
                managed_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                f"{managed_policy_change_model.arn} is not attached to this role",
                str(e),
            )

        # Trying to attach a policy that is already attached
        role.managed_policies = [{"PolicyArn": managed_policy_change_model.arn}]
        managed_policy_change_model.action = Action.attach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_change(
                managed_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                f"{managed_policy_change_model.arn} already attached to this role",
                str(e),
            )

        # Valid tests

        # Attach a managed policy that is not attached
        managed_policy_change_model.arn = (
            "arn:aws:iam::123456789012:policy/TestManagedPolicy2"
        )
        managed_policy_change_model.action = Action.attach
        await validate_managed_policy_change(
            managed_policy_change_model, "user@example.com", role
        )

        # Detach a managed policy that is attached to the role
        role.managed_policies = [{"PolicyArn": managed_policy_change_model.arn}]
        managed_policy_change_model.action = Action.detach
        await validate_managed_policy_change(
            managed_policy_change_model, "user@example.com", role
        )

    async def test_validate_managed_policy_resource_change(self):
        from common.exceptions.exceptions import InvalidRequestParameter
        from common.lib.v2.requests import validate_managed_policy_resource_change

        managed_policy_change = {
            "principal": {
                "principal_arn": "arn:aws:iam::123456789012:policy/test",
                "principal_type": "AwsResource",
            },
            "change_type": "managed_policy_resource",
            "resources": [],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                            ],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        managed_policy_change_model = ManagedPolicyResourceChangeModel.parse_obj(
            managed_policy_change
        )

        # Trying to update a policy that doesn't exist
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_resource_change(
                managed_policy_change_model, test_role_name, "user@example.com", None
            )
        self.assertIn("doesn't exist", str(e))

        # Trying to update a policy with no changes
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_resource_change(
                managed_policy_change_model,
                test_role_name,
                "user@example.com",
                managed_policy_change_model.policy.policy_document,
            )
        self.assertIn("No changes detected", str(e))

        # Valid, should pass
        await validate_managed_policy_resource_change(
            managed_policy_change_model,
            test_role_name,
            "user@example.com",
            {"Version": "2012-10-17", "Statement": []},
        )

    async def test_validate_permissions_boundary_change(self):
        from common.exceptions.exceptions import InvalidRequestParameter
        from common.lib.v2.requests import validate_permissions_boundary_change

        role = ExtendedAwsPrincipalModel(
            name="role_name",
            account_id="123456789012",
            account_name="friendly_name",
            arn=test_role_arn,
            inline_policies=[],
            assume_role_policy_document={},
            managed_policies=[],
            permissions_boundary={},
            tags=[],
        )
        permissions_boundary_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "permissions_boundary",
            "policy_name": "invalid<html>characters",
            "resources": [],
            "status": "not_applied",
            "action": "detach",
            "arn": "arn:aws:iam::123456789012:policy/TestManagedPolicy",
        }
        permissions_boundary_change_model = PermissionsBoundaryChangeModel.parse_obj(
            permissions_boundary_change
        )

        # Trying to update an managed policy with invalid characters
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_permissions_boundary_change(
                permissions_boundary_change_model, "user@example.com", role
            )
            self.assertIn("Invalid characters were detected in the policy.", str(e))

        # Trying to detach a policy that is not attached
        permissions_boundary_change_model.action = Action.detach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_permissions_boundary_change(
                permissions_boundary_change_model, "user@example.com", role
            )
            self.assertIn(
                f"{permissions_boundary_change_model.arn}  is not attached to this role as a permissions boundary",
                str(e),
            )

        # Valid tests

        # Attach a managed policy that is not attached
        permissions_boundary_change_model.arn = (
            "arn:aws:iam::123456789012:policy/TestManagedPolicy2"
        )
        permissions_boundary_change_model.action = Action.attach
        await validate_permissions_boundary_change(
            permissions_boundary_change_model, "user@example.com", role
        )

        # Detach a managed policy that is attached to the role
        role.permissions_boundary = {
            "PermissionsBoundaryArn": permissions_boundary_change_model.arn
        }
        permissions_boundary_change_model.action = Action.detach
        await validate_permissions_boundary_change(
            permissions_boundary_change_model, "user@example.com", role
        )

    async def test_validate_assume_role_policy_change(self):
        from common.exceptions.exceptions import InvalidRequestParameter
        from common.lib.v2.requests import validate_assume_role_policy_change

        role = ExtendedAwsPrincipalModel(
            name="role_name",
            account_id="123456789012",
            account_name="friendly_name",
            arn=test_role_arn,
            inline_policies=[],
            assume_role_policy_document={},
            managed_policies=[],
            tags=[],
        )
        assume_role_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "assume_role_policy",
            "resources": [],
            "status": "not_applied",
            "new": True,
            "policy": {
                "version": "<>>",
                "policy_document": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        assume_role_policy_change_model = AssumeRolePolicyChangeModel.parse_obj(
            assume_role_policy_change
        )

        # Trying to update an assume role policy with invalid characters
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_assume_role_policy_change(
                assume_role_policy_change_model, "user@example.com", role
            )
            self.assertIn("Invalid characters were detected in the policy", str(e))

        assume_role_policy_change_model.policy.version = None

        # Updating the same assume role policy as current document
        role.assume_role_policy_document = (
            assume_role_policy_change_model.policy.policy_document
        )
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_assume_role_policy_change(
                assume_role_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                "No changes were found between the updated and existing assume role policy.",
                str(e),
            )

        # Valid test: updating assume role policy document with no invalid characters
        role.assume_role_policy_document = {}
        await validate_assume_role_policy_change(
            assume_role_policy_change_model, "user@example.com", role
        )

    async def test_generate_resource_policies(self):
        from common.aws.utils import ResourceAccountCache
        from common.lib.v2.requests import generate_resource_policies

        if not ResourceAccountCache._tenant_resources.get(tenant):
            ResourceAccountCache._tenant_resources[tenant] = TTLCache(
                maxsize=1000, ttl=120
            )
        ResourceAccountCache._tenant_resources[tenant][
            "arn:aws:s3:::test_bucket"
        ] = "123456789013"
        ResourceAccountCache._tenant_resources[tenant][
            "arn:aws:s3:::test_bucket_2"
        ] = "123456789013"

        inline_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "inline_policy",
            "resources": [
                {
                    "arn": "arn:aws:s3:::test_bucket",
                    "name": "test_bucket",
                    "account_id": "",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "s3",
                },
                {
                    "arn": "arn:aws:s3:::test_bucket_2",
                    "name": "test_bucket_2",
                    "account_id": "",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "s3",
                },
                {
                    "arn": "arn:aws:iam::123456789013:role/test_2",
                    "name": "test_2",
                    "account_id": "123456789013",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "iam",
                },
                {
                    "arn": "arn:aws:iam::123456789012:role/test_3",
                    "name": "test_3",
                    "account_id": "123456789012",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "iam",
                },
                {
                    "arn": "arn:aws:iam::123456789013:role/test_3",
                    "name": "test_3",
                    "account_id": "123456789013",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "iam",
                },
            ],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                                "arn:aws:s3:::test_bucket_2",
                                "arn:aws:S3:::test_bucket_2/*",
                            ],
                            "Sid": "sid_test",
                        },
                        {
                            "Action": ["sts:AssumeRole", "sts:TagSession"],
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789013:role/test_2"],
                            "Sid": "assume_role_test_cross_account",
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789012:role/test_3"],
                            "Sid": "assume_role_test_same_account",
                        },
                        {
                            "Action": "sts:TagSession",
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789013:role/test_3"],
                            "Sid": "assume_role_test_cross_account_tag",
                        },
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        managed_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "managed_policy",
            "policy_name": "invalid<html>characters",
            "resources": [],
            "status": "not_applied",
            "action": "detach",
            "arn": "arn:aws:iam::123456789012:policy/TestManagedPolicy",
        }
        managed_policy_change_model = ManagedPolicyChangeModel.parse_obj(
            managed_policy_change
        )

        request_changes = {
            "changes": [inline_policy_change_model, managed_policy_change_model]
        }
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
            changes=request_changes,
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )
        len_before_call = len(extended_request.changes.changes)
        number_of_resources = 5
        await generate_resource_policies(
            extended_request, extended_request.requester_email, tenant
        )
        self.assertEqual(
            len(extended_request.changes.changes), len_before_call + number_of_resources
        )
        self.assertEqual(
            inline_policy_change_model.policy,
            extended_request.changes.changes[0].policy,
        )
        self.assertEqual(
            len(inline_policy_change_model.resources),
            len(extended_request.changes.changes[0].resources),
        )
        self.assertIn(managed_policy_change_model, extended_request.changes.changes)

        seen_resource_one = False
        seen_resource_two = False
        seen_resource_three = False
        seen_resource_four = False
        for change in extended_request.changes.changes:
            if (
                change.change_type == "resource_policy"
                and change.arn == inline_policy_change_model.resources[0].arn
            ):
                seen_resource_one = True
                self.assertTrue(change.autogenerated)
            elif (
                change.change_type == "resource_policy"
                and change.arn == inline_policy_change_model.resources[1].arn
            ):
                seen_resource_two = True
                self.assertTrue(change.autogenerated)
            elif (
                change.change_type == "sts_resource_policy"
                and change.arn == inline_policy_change_model.resources[2].arn
            ):
                seen_resource_three = True
                self.assertTrue(change.autogenerated)
            elif (
                change.change_type == "sts_resource_policy"
                and change.arn == inline_policy_change_model.resources[4].arn
            ):
                seen_resource_four = True
                self.assertTrue(change.autogenerated)

        self.assertTrue(seen_resource_one)
        self.assertTrue(seen_resource_two)
        self.assertTrue(seen_resource_three)
        self.assertTrue(seen_resource_four)
        ResourceAccountCache._tenant_resources[tenant].pop("arn:aws:s3:::test_bucket")
        ResourceAccountCache._tenant_resources[tenant].pop("arn:aws:s3:::test_bucket_2")

    async def test_apply_changes_to_role_inline_policy(self):
        from common.config import config
        from common.lib.v2.requests import apply_changes_to_role

        inline_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": True,
            "action": "detach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                            ],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
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

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )

        # Detaching inline policy that isn't attached -> error
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(1, response.errors)
        self.assertIn(
            "Error occurred deleting inline policy",
            dict(response.action_results[0]).get("message"),
        )

        # Attaching inline policy -> no error
        response.action_results = []
        response.errors = 0
        inline_policy_change_model.action = Action.attach
        extended_request.changes = ChangeModelArray(
            changes=[inline_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(0, response.errors)
        self.assertIn(
            "Successfully applied inline policy",
            dict(response.action_results[0]).get("message", ""),
        )
        # Make sure it attached
        inline_policy = client.get_role_policy(
            RoleName=test_role_name, PolicyName=inline_policy_change_model.policy_name
        )
        self.assertEqual(
            inline_policy_change_model.policy_name, inline_policy.get("PolicyName")
        )
        self.assertEqual(
            inline_policy_change_model.policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )

        # Updating the inline policy -> no error
        inline_policy_change_model.policy.policy_document.get("Statement")[0][
            "Effect"
        ] = "Deny"
        inline_policy_change_model.status = "not_applied"
        extended_request.changes = ChangeModelArray(
            changes=[inline_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(0, response.errors)
        self.assertIn(
            "Successfully applied inline policy",
            dict(response.action_results[0]).get("message", ""),
        )
        # Make sure it updated
        inline_policy = client.get_role_policy(
            RoleName=test_role_name, PolicyName=inline_policy_change_model.policy_name
        )
        self.assertEqual(
            inline_policy_change_model.policy_name, inline_policy.get("PolicyName")
        )
        self.assertEqual(
            inline_policy_change_model.policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )

        # Detach the above attached inline policy -> no error, should be detached
        response.action_results = []
        response.errors = 0
        inline_policy_change_model.action = Action.detach
        inline_policy_change_model.status = "not_applied"
        extended_request.changes = ChangeModelArray(
            changes=[inline_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(0, response.errors)
        with pytest.raises(client.exceptions.NoSuchEntityException) as e:
            # check to make sure it's detached
            client.get_role_policy(
                RoleName=test_role_name,
                PolicyName=inline_policy_change_model.policy_name,
            )
            self.assertIn("not attached to role", str(e))

    async def test_apply_changes_to_role_managed_policy(self):
        from common.config import config
        from common.lib.v2.requests import apply_changes_to_role

        managed_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "managed_policy",
            "policy_name": "TestManagedPolicy",
            "resources": [],
            "status": "not_applied",
            "action": "detach",
            "arn": "arn:aws:iam::123456789012:policy/TestManagedPolicy",
        }
        managed_policy_change_model = ManagedPolicyChangeModel.parse_obj(
            managed_policy_change
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
            changes=ChangeModelArray(changes=[managed_policy_change]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )

        # Detaching a managed policy that's not attached
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(1, response.errors)
        self.assertIn(
            "Error occurred detaching managed policy",
            dict(response.action_results[0]).get("message"),
        )

        # Trying to attach a managed policy that doesn't exist
        response.action_results = []
        response.errors = 0
        managed_policy_change_model.action = Action.attach
        extended_request.changes = ChangeModelArray(
            changes=[managed_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(1, response.errors)
        self.assertIn(
            "Error occurred attaching managed policy",
            dict(response.action_results[0]).get("message"),
        )

        managed_policy_sample = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["s3:Get*", "s3:List*"], "Resource": "*"}
            ],
        }

        client.create_policy(
            PolicyName=managed_policy_change["policy_name"],
            PolicyDocument=json.dumps(managed_policy_sample),
        )

        # Attaching a managed policy that exists -> no errors
        response.action_results = []
        response.errors = 0
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(0, response.errors)
        # Make sure it attached
        role_attached_policies = client.list_attached_role_policies(
            RoleName=test_role_name
        )
        self.assertEqual(len(role_attached_policies.get("AttachedPolicies")), 1)
        self.assertEqual(
            role_attached_policies.get("AttachedPolicies")[0].get("PolicyArn"),
            managed_policy_change_model.arn,
        )

        # Detaching the managed policy -> no errors
        response.action_results = []
        response.errors = 0
        managed_policy_change_model.action = Action.detach
        managed_policy_change_model.status = "not_applied"
        extended_request.changes = ChangeModelArray(
            changes=[managed_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(0, response.errors)
        # Make sure it detached
        role_attached_policies = client.list_attached_role_policies(
            RoleName=test_role_name
        )
        self.assertEqual(len(role_attached_policies.get("AttachedPolicies")), 0)

    async def test_apply_changes_to_role_assume_role_policy(self):
        from common.config import config
        from common.lib.v2.requests import apply_changes_to_role

        assume_role_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "assume_role_policy",
            "resources": [],
            "status": "not_applied",
            "new": True,
            "policy": {
                "version": "<>>",
                "policy_document": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        assume_role_policy_change_model = AssumeRolePolicyChangeModel.parse_obj(
            assume_role_policy_change
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
            changes=ChangeModelArray(changes=[assume_role_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )

        # Attach the assume role policy document -> no errors
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(0, response.errors)
        # Make sure it attached
        role_details = client.get_role(RoleName=test_role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            assume_role_policy_change_model.policy.policy_document,
        )

    async def test_apply_changes_to_role_unsupported_change(self):
        from common.lib.v2.requests import apply_changes_to_role

        resource_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "resource_policy",
            "resources": [
                {
                    "arn": test_role_arn,
                    "name": test_role_name,
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:s3:::test_bucket",
            "autogenerated": False,
            "policy": {
                "policy_document": {"Version": "2012-10-17", "Statement": []},
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
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
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        # Not supported change -> Error
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant
        )
        self.assertEqual(1, response.errors)
        self.assertIn("Error occurred", dict(response.action_results[0]).get("message"))
        self.assertIn("not supported", dict(response.action_results[0]).get("message"))

    async def test_apply_specific_change_to_role(self):
        from common.config import config
        from common.lib.v2.requests import apply_changes_to_role

        assume_role_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "assume_role_policy",
            "resources": [],
            "status": "not_applied",
            "new": True,
            "id": "12345",
            "policy": {
                "version": "2.0",
                "policy_document": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        assume_role_policy_change_model = AssumeRolePolicyChangeModel.parse_obj(
            assume_role_policy_change
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
            changes=ChangeModelArray(changes=[assume_role_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        client.update_assume_role_policy(
            RoleName=test_role_name,
            PolicyDocument=json.dumps(
                {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
            ),
        )
        # Specify ID different from change -> No changes should happen
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, tenant, "1234"
        )
        self.assertEqual(0, response.errors)
        self.assertEqual(0, len(response.action_results))
        # Make sure the change didn't occur
        role_details = client.get_role(RoleName=test_role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": "arn:aws:iam::123456789012:role/myProfile"
                        },
                        "Sid": "AllowMeToAssumePlease",
                    }
                ],
                "Version": "2012-10-17",
            },
        )

        # Specify ID same as change -> Change should happen
        await apply_changes_to_role(
            extended_request,
            response,
            extended_request.requester_email,
            tenant,
            assume_role_policy_change_model.id,
        )
        self.assertEqual(0, response.errors)
        self.assertEqual(1, len(response.action_results))
        # Make sure the change occurred
        role_details = client.get_role(RoleName=test_role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            assume_role_policy_change_model.policy.policy_document,
        )

    @pytest.mark.skip(reason="EN-637")
    async def test_populate_old_policies(self):
        from common.config import config
        from common.lib.v2.requests import populate_old_policies

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        client.put_role_policy(
            RoleName=test_role_name,
            PolicyName=existing_policy_name,
            PolicyDocument=json.dumps(existing_policy_document),
        )

        inline_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "applied",
            "policy_name": existing_policy_name,
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {},
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
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

        # role = ExtendedAwsPrincipalModel(
        #     name="role_name",
        #     account_id="123456789012",
        #     account_name="friendly_name",
        #     arn=test_role_arn,
        #     inline_policies=[
        #         {
        #             "PolicyName": inline_policy_change_model.policy_name,
        #             "PolicyDocument": existing_policy_document,
        #         }
        #     ],
        #     assume_role_policy_document={},
        #     managed_policies=[],
        #     tags=[],
        # )

        # assert before calling this function that old policy is None
        self.assertEqual(None, extended_request.changes.changes[0].old_policy)

        extended_request = await populate_old_policies(
            extended_request, extended_request.requester_email, tenant
        )

        # assert after calling this function that old policy is None, we shouldn't modify changes that are already
        # applied
        self.assertEqual(None, extended_request.changes.changes[0].old_policy)

        extended_request.changes.changes[0].status = Status.not_applied
        # assert before calling this function that old policy is None
        self.assertEqual(None, extended_request.changes.changes[0].old_policy)

        extended_request = await populate_old_policies(
            extended_request, extended_request.requester_email, tenant
        )

        # assert after calling the function that the old policies populated properly
        self.assertDictEqual(
            existing_policy_document,
            extended_request.changes.changes[0].old_policy.policy_document,
        )

    async def test_populate_old_managed_policies(self):
        from common.config import config
        from common.lib.v2.requests import populate_old_managed_policies

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        for path in ["/", "/testpath/test2/"]:
            client.create_policy(
                PolicyName=existing_policy_name + "managed",
                PolicyDocument=json.dumps(existing_policy_document),
                Path=path,
            )
            policy_name_and_path = path + existing_policy_name + "managed"
            managed_policy_resource_change = {
                "principal": {
                    "principal_arn": f"arn:aws:iam::123456789012:policy{policy_name_and_path}",
                    "principal_type": "AwsResource",
                },
                "change_type": "managed_policy_resource",
                "resources": [],
                "version": 2.0,
                "status": "applied",
                "new": False,
                "policy": {
                    "version": None,
                    "policy_document": {},
                    "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
                },
                "old_policy": None,
            }
            managed_policy_resource_change = ManagedPolicyResourceChangeModel.parse_obj(
                managed_policy_resource_change
            )

            extended_request = ExtendedRequestModel(
                id="1234",
                principal=dict(
                    principal_type="AwsResource",
                    principal_arn=f"arn:aws:iam::123456789012:policy{policy_name_and_path}",
                ),
                timestamp=int(time.time()),
                justification="Test justification",
                requester_email="user@example.com",
                approvers=[],
                request_status="pending",
                changes=ChangeModelArray(changes=[managed_policy_resource_change]),
                requester_info=UserModel(email="user@example.com"),
                comments=[],
            )

            # assert before calling this function that old policy is None
            self.assertEqual(None, extended_request.changes.changes[0].old_policy)

            await populate_old_managed_policies(
                extended_request, extended_request.requester_email, tenant
            )

            # assert after calling this function that old policy is None, we shouldn't modify changes that are already
            # applied
            self.assertEqual(None, extended_request.changes.changes[0].old_policy)

            extended_request.changes.changes[0].status = Status.not_applied
            # assert before calling this function that old policy is None
            self.assertEqual(None, extended_request.changes.changes[0].old_policy)

            await populate_old_managed_policies(
                extended_request, extended_request.requester_email, tenant
            )

            # assert after calling the function that the old policies populated properly
            self.assertDictEqual(
                existing_policy_document,
                extended_request.changes.changes[0].old_policy.policy_document,
            )

    async def test_apply_managed_policy_resource_change(self):
        from common.config import config
        from common.lib.v2.requests import apply_managed_policy_resource_change

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        for path in ["/", "/testpath/test2/"]:
            policy_name_and_path = path + existing_policy_name + "managed2"
            managed_policy_resource_change = {
                "principal": {
                    "principal_arn": f"arn:aws:iam::123456789012:policy{policy_name_and_path}",
                    "principal_type": "AwsResource",
                },
                "change_type": "managed_policy_resource",
                "resources": [],
                "version": 2.0,
                "status": "not_applied",
                "new": True,
                "policy": {
                    "version": None,
                    "policy_document": existing_policy_document,
                    "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
                },
                "old_policy": None,
            }
            managed_policy_resource_change = ManagedPolicyResourceChangeModel.parse_obj(
                managed_policy_resource_change
            )

            extended_request = ExtendedRequestModel(
                id="1234",
                principal=dict(
                    principal_type="AwsResource",
                    principal_arn=f"arn:aws:iam::123456789012:policy{policy_name_and_path}",
                ),
                timestamp=int(time.time()),
                justification="Test justification",
                requester_email="user@example.com",
                approvers=[],
                request_status="pending",
                changes=ChangeModelArray(changes=[managed_policy_resource_change]),
                requester_info=UserModel(email="user@example.com"),
                comments=[],
            )
            response = PolicyRequestModificationResponseModel(
                errors=0, action_results=[]
            )

            # should create a new managed policy
            response = await apply_managed_policy_resource_change(
                extended_request,
                managed_policy_resource_change,
                response,
                "test@example.com",
                tenant,
            )
            self.assertEqual(0, response.errors)
            self.assertIn(
                "created managed policy",
                dict(response.action_results[0]).get("message"),
            )
            # ensure that it has been created in AWS
            policy_response = client.get_policy(
                PolicyArn=extended_request.principal.principal_arn
            )["Policy"]
            self.assertEqual(
                policy_response["PolicyName"], existing_policy_name + "managed2"
            )
            self.assertEqual(policy_response["Path"], path)
            policy_response_detailed = client.get_policy_version(
                PolicyArn=extended_request.principal.principal_arn,
                VersionId=policy_response["DefaultVersionId"],
            )["PolicyVersion"]
            self.assertDictEqual(
                policy_response_detailed["Document"], existing_policy_document
            )

            # update existing policy document
            managed_policy_resource_change.policy.policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            "s3:ListBucket",
                        ],
                        "Effect": "Allow",
                        "Resource": ["arn:aws:s3:::test_bucket"],
                        "Sid": "sid_test23",
                    }
                ],
            }
            managed_policy_resource_change.status = Status.not_applied
            managed_policy_resource_change.new = False
            extended_request.changes = ChangeModelArray(
                changes=[managed_policy_resource_change]
            )
            response = PolicyRequestModificationResponseModel(
                errors=0, action_results=[]
            )

            response = await apply_managed_policy_resource_change(
                extended_request,
                managed_policy_resource_change,
                response,
                "test@example.com",
                tenant,
            )

            self.assertEqual(0, response.errors)
            self.assertIn(
                "updated managed policy",
                dict(response.action_results[0]).get("message"),
            )
            # ensure that it has been updated in AWS
            policy_response = client.get_policy(
                PolicyArn=extended_request.principal.principal_arn
            )["Policy"]
            self.assertEqual(
                policy_response["PolicyName"], existing_policy_name + "managed2"
            )
            self.assertEqual(policy_response["Path"], path)
            policy_response_detailed = client.get_policy_version(
                PolicyArn=extended_request.principal.principal_arn,
                VersionId=policy_response["DefaultVersionId"],
            )["PolicyVersion"]
            self.assertDictEqual(
                policy_response_detailed["Document"],
                managed_policy_resource_change.policy.policy_document,
            )

    # TODO: tag_policy hasn't been implemented in moto3 yet (https://github.com/spulec/moto/blob/master/IMPLEMENTATION_COVERAGE.md)
    # This test will have to wait until it has been implemented
    # async def test_apply_managed_policy_resource_tag_change(self):
    #     from common.lib.v2.requests import apply_managed_policy_resource_tag_change
    #
    #     client = boto3.client("iam", region_name="us-east-1", **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}))
    #
    #     managed_policy_resource_tag_change = {
    #         "principal": {
    #             "principal_arn": f"arn:aws:iam::123456789012:policy/policy-one",
    #             "principal_type": "AwsResource",
    #         },
    #         "change_type": "resource_tag",
    #         "resources": [],
    #         "version": 2.0,
    #         "status": "not_applied",
    #         "key": "testkey",
    #         "value": "testvalue",
    #         "tag_action": "create"
    #     }
    #     managed_policy_resource_tag_change_model = ResourceTagChangeModel.parse_obj(
    #         managed_policy_resource_tag_change
    #     )
    #
    #     extended_request = ExtendedRequestModel(
    #         id="1234",
    #         principal=dict(
    #             principal_type="AwsResource",
    #             principal_arn=f"arn:aws:iam::123456789012:policy/policy-one",
    #         ),
    #         timestamp=int(time.time()),
    #         justification="Test justification",
    #         requester_email="user@example.com",
    #         approvers=[],
    #         request_status="pending",
    #         changes=ChangeModelArray(changes=[managed_policy_resource_tag_change_model]),
    #         requester_info=UserModel(email="user@example.com"),
    #         comments=[],
    #     )
    #     response = PolicyRequestModificationResponseModel(errors=0, action_results=[])
    #
    #     # should add a new tag to managed policy
    #     response = await apply_managed_policy_resource_tag_change(
    #         extended_request,
    #         managed_policy_resource_tag_change_model,
    #         response,
    #         "test@example.com",
    #     )
    #
    #     self.assertEqual(0, response.errors)
    #     self.assertIn(
    #         "created or updated tag", dict(response.action_results[0]).get("message")
    #     )
    #     # ensure that it has been created in AWS
    #     policy_response = client.get_policy(
    #         PolicyArn=extended_request.principal.principal_arn
    #     )["TagSet"]
    #     self.assertEqual(1, len(policy_response))

    async def test_apply_resource_policy_change_unsupported(self):
        from common.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "resources": [
                {
                    "arn": test_role_arn,
                    "name": test_role_name,
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:unsupported::123456789012:test_not_supported",
            "autogenerated": False,
            "policy": {
                "policy_document": {"Version": "2012-10-17", "Statement": []},
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
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
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # Not supported change -> Error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(1, response.errors)
        self.assertIn(
            "Cannot apply change", dict(response.action_results[0]).get("message")
        )
        self.assertIn("not supported", dict(response.action_results[0]).get("message"))

    async def test_apply_resource_policy_change_iam(self):
        from common.config import config
        from common.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "sts_resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": test_role_arn,
                    "name": test_role_name,
                    "account_id": "123456789012",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:iam::123456789012:role/test_2",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sts:AssumeRole", "sts:TagSession"],
                            "Effect": "Allow",
                            "Principal": {"AWS": [test_role_arn]},
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
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
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # Role doesn't exist -> applying policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn("NoSuchEntity", dict(response.action_results[0]).get("message"))
        self.assertEqual(Status.not_applied, resource_policy_change_model.status)

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        role_name = "test_2"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        response.errors = 0
        response.action_results = []

        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )
        self.assertEqual(0, response.errors)
        # Make sure it attached
        role_details = client.get_role(RoleName=role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            resource_policy_change_model.policy.policy_document,
        )

        # Ensure the request got updated
        self.assertEqual(Status.applied, resource_policy_change_model.status)

    async def test_apply_resource_policy_change_s3(self):
        from common.config import config
        from common.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": test_role_arn,
                    "name": test_role_name,
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:s3::123456789012:test_bucket",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [test_role_arn],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
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
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # Bucket doesn't exist -> applying policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn("NoSuchBucket", dict(response.action_results[0]).get("message"))

        conn = boto3.resource(
            "s3",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        conn.create_bucket(Bucket="test_bucket")
        response.errors = 0
        response.action_results = []
        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(0, response.errors)
        # Check to make sure bucket policy got updated
        bucket_policy = conn.BucketPolicy("test_bucket")
        self.assertDictEqual(
            json.loads(bucket_policy.policy),
            resource_policy_change_model.policy.policy_document,
        )

    @pytest.mark.usefixtures("sqs")
    async def test_apply_resource_policy_change_sqs(self):
        from common.config import config
        from common.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": test_role_arn,
                    "name": test_role_name,
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:sqs:us-east-1:123456789012:test_sqs",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sqs: *"],
                            "Effect": "Allow",
                            "Resource": [test_role_arn],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
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
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # SQS doesn't exist -> applying SQS policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn(
            "NonExistentQueue", dict(response.action_results[0]).get("message")
        )

        client = boto3.client(
            "sqs",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        client.create_queue(QueueName="test_sqs")
        response.errors = 0
        response.action_results = []
        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(0, response.errors)
        # Check to make sure queue attribute
        queue_url = client.get_queue_url(QueueName="test_sqs")
        attributes = client.get_queue_attributes(
            QueueUrl=queue_url.get("QueueUrl"), AttributeNames=["All"]
        )
        self.assertDictEqual(
            json.loads(attributes.get("Attributes").get("Policy")),
            resource_policy_change_model.policy.policy_document,
        )

    @pytest.mark.usefixtures("sns")
    async def test_apply_resource_policy_change_sns(self):
        from common.config import config
        from common.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": test_role_arn,
                    "name": test_role_name,
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:sns:us-east-1:123456789012:test_sns",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sns: *"],
                            "Effect": "Allow",
                            "Resource": [test_role_arn],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
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
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # SNS doesn't exist -> applying SNS policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn("NotFound", dict(response.action_results[0]).get("message"))

        client = boto3.client(
            "sns",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        client.create_topic(Name="test_sns")
        response.errors = 0
        response.action_results = []
        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
            tenant,
        )

        self.assertEqual(0, response.errors)
        # Check to make sure sns attribute
        attributes = client.get_topic_attributes(
            TopicArn=resource_policy_change_model.arn
        )
        self.assertDictEqual(
            json.loads(attributes.get("Attributes").get("Policy")),
            resource_policy_change_model.policy.policy_document,
        )

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("dynamodb")
    @pytest.mark.usefixtures("populate_caches")
    @patch("common.lib.v2.requests.send_communications_new_comment")
    @patch("common.user_request.models.IAMRequest.write_v2")
    async def test_parse_and_apply_policy_request_modification_add_comment(
        self, mock_dynamo_write, mock_send_comment
    ):
        from common.lib.v2.requests import parse_and_apply_policy_request_modification

        extended_request = await get_extended_request_helper()
        input_body = {"modification_model": {"command": "add_comment"}}

        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = None
        mock_send_comment.return_value = None
        # Trying to set an empty comment
        with pytest.raises(ValidationError) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn("validation error", str(e))

        input_body["modification_model"]["comment_text"] = "Sample comment"
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )

        # It fails when I try to add the patch as a decorator. This may have to do with the import inside the function.
        with patch("smtplib.SMTP_SSL", autospec=True):
            response = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
                tenant,
            )
        self.assertEqual(0, response.errors)
        # Make sure comment got added to the request
        self.assertEqual(1, len(extended_request.comments))
        comment = extended_request.comments[0]
        self.assertEqual(comment.user_email, "user2@example.com")
        self.assertEqual(comment.text, "Sample comment")

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("dynamodb")
    @pytest.mark.usefixtures("populate_caches")
    @pytest.mark.usefixtures("iam")
    # @patch("common.user_request.models.IAMRequest.write_v2")
    async def test_parse_and_apply_policy_request_modification_update_expiration_date(
        self,
    ):
        from common.lib.v2.requests import parse_and_apply_policy_request_modification

        extended_request = await get_extended_request_helper()
        input_body = {
            "modification_model": {
                "command": Command.update_expiration_date,
                "expiration_date": None,
            }
        }

        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp

        # Trying to set an empty expiration_date
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "user2@example.com",
            [],
            last_updated,
            tenant,
        )
        self.assertEqual(0, response.errors)
        self.assertEqual(extended_request.expiration_date, None)

        input_body["modification_model"]["expiration_date"] = 20220407
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "user2@example.com",
            [],
            last_updated,
            tenant,
        )
        self.assertEqual(0, response.errors)
        self.assertEqual(extended_request.expiration_date, 20220407)

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("populate_caches")
    @pytest.mark.usefixtures("dynamodb")
    @patch("common.user_request.models.IAMRequest.write_v2")
    async def test_parse_and_apply_policy_request_modification_update_change(
        self, mock_dynamo_write
    ):
        from common.lib.v2.requests import parse_and_apply_policy_request_modification

        extended_request = await get_extended_request_helper()
        updated_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:*"],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::test_bucket",
                        "arn:aws:s3:::test_bucket/abc/*",
                    ],
                    "Sid": "sid_test",
                }
            ],
        }
        input_body = {
            "modification_model": {
                "command": "update_change",
                "change_id": extended_request.changes.changes[0].id,
                "policy_document": updated_policy_doc,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = None

        # Trying to update while not being authorized
        from common.exceptions.exceptions import Unauthorized

        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn("Unauthorized", str(e))

        # Trying to update a non-existent change
        from common.exceptions.exceptions import NoMatchingRequest

        policy_request_model.modification_model.change_id = (
            extended_request.changes.changes[0].id + "non-existent"
        )
        with pytest.raises(NoMatchingRequest) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn("Unable to find", str(e))

        # Valid change to be updated
        policy_request_model.modification_model.change_id = (
            extended_request.changes.changes[0].id
        )
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "user@example.com",
            [],
            last_updated,
            tenant,
        )
        self.assertEqual(0, response.errors)
        # Make sure change got updated in the request
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            updated_policy_doc,
        )

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("dynamodb")
    @pytest.mark.usefixtures("populate_caches")
    @patch("common.lib.v2.requests.populate_old_policies")
    @patch("common.user_request.models.IAMRequest.write_v2")
    @patch("common.lib.v2.requests.can_admin_policies")
    async def test_parse_and_apply_policy_request_modification_apply_change(
        self,
        can_admin_policies,
        mock_dynamo_write,
        mock_populate_old_policies,
    ):
        from common.config import config
        from common.exceptions.exceptions import NoMatchingRequest, Unauthorized
        from common.lib.v2.requests import parse_and_apply_policy_request_modification

        extended_request = await get_extended_request_helper()
        updated_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:*"],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::test_bucket",
                        "arn:aws:s3:::test_bucket/abc/*",
                    ],
                    "Sid": "sid_test",
                }
            ],
        }
        input_body = {
            "modification_model": {
                "command": "apply_change",
                "change_id": extended_request.changes.changes[0].id,
                "policy_document": updated_policy_doc,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = None
        mock_populate_old_policies.return_value = extended_request
        # mock_fetch_iam_role.return_value = None
        can_admin_policies.return_value = False
        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )

        # Trying to apply while not being authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn("Unauthorized", str(e))

        can_admin_policies.return_value = True
        # Trying to apply a non-existent change

        policy_request_model.modification_model.change_id = (
            extended_request.changes.changes[0].id + "non-existent"
        )

        with pytest.raises(NoMatchingRequest) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "consoleme_admins@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn("Unable to find", str(e))

        # Valid change to be applied
        policy_request_model.modification_model.change_id = (
            extended_request.changes.changes[0].id
        )

        # It fails when I try to add the patch as a decorator. Possibly due to the import in this method.
        with patch("smtplib.SMTP_SSL", autospec=True):
            response = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
                tenant,
                approval_rule_approved=True,
            )

        self.assertEqual(0, response.errors)
        # Make sure change got updated in the request
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            updated_policy_doc,
        )
        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)
        # Make sure this change got applied
        inline_policy = client.get_role_policy(
            RoleName=test_role_name,
            PolicyName=extended_request.changes.changes[0].policy_name,
        )
        self.assertEqual(
            extended_request.changes.changes[0].policy_name,
            inline_policy.get("PolicyName"),
        )
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("dynamodb")
    @pytest.mark.usefixtures("populate_caches")
    @patch("common.lib.v2.requests.send_communications_policy_change_request_v2")
    @patch("common.user_request.models.IAMRequest.write_v2")
    async def test_parse_and_apply_policy_request_modification_cancel_request(
        self, mock_dynamo_write, mock_write_policy
    ):
        from common.exceptions.exceptions import InvalidRequestParameter, Unauthorized
        from common.lib.v2.requests import parse_and_apply_policy_request_modification

        extended_request = await get_extended_request_helper()

        input_body = {"modification_model": {"command": "cancel_request"}}
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = None
        mock_write_policy.return_value = None
        # Trying to cancel while not being authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn("Unauthorized", str(e))

        extended_request.changes.changes[0].status = Status.applied

        # It fails when I try to add the patch as a decorator.
        with patch("smtplib.SMTP_SSL", autospec=True):
            # Trying to cancel while at least one change is applied
            res = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn(
                res.action_results[0].message,
                "Request cannot be cancelled because at least one change has been applied already. "
                "Please apply or cancel the other changes.",
            )
            extended_request.changes.changes[0].status = Status.not_applied

            # Trying to cancel an approved request
            extended_request.request_status = RequestStatus.approved
            with pytest.raises(InvalidRequestParameter) as e:
                await parse_and_apply_policy_request_modification(
                    extended_request,
                    policy_request_model,
                    "user@example.com",
                    [],
                    last_updated,
                    tenant,
                )
                self.assertIn("cannot be cancelled", str(e))

            # Cancelling valid request
            extended_request.request_status = RequestStatus.pending
            response = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertEqual(0, response.errors)
            # Make sure request got cancelled
            self.assertEqual(RequestStatus.cancelled, extended_request.request_status)

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("dynamodb")
    @pytest.mark.usefixtures("populate_caches")
    @patch("common.lib.v2.requests.send_communications_policy_change_request_v2")
    @patch("common.lib.v2.requests.can_move_back_to_pending_v2")
    @patch("common.user_request.models.IAMRequest.write_v2")
    async def test_parse_and_apply_policy_request_modification_reject_and_move_back_to_pending_request(
        self, mock_dynamo_write, mock_move_back_to_pending, mock_send_email
    ):
        from common.exceptions.exceptions import InvalidRequestParameter, Unauthorized
        from common.lib.v2.requests import parse_and_apply_policy_request_modification

        extended_request = await get_extended_request_helper()

        input_body = {"modification_model": {"command": "reject_request"}}
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = int(extended_request.timestamp.timestamp())
        mock_dynamo_write.return_value = None
        mock_send_email.return_value = None

        # It fails when I try to add the patch as a decorator. Possibly due to the import in this method.
        with patch("smtplib.SMTP_SSL", autospec=True):
            # Trying to reject while not being authorized
            with pytest.raises(Unauthorized) as e:
                await parse_and_apply_policy_request_modification(
                    extended_request,
                    policy_request_model,
                    "user2@example.com",
                    [],
                    last_updated,
                    tenant,
                )
                self.assertIn("Unauthorized", str(e))
            extended_request.changes.changes[0].status = Status.applied
            # Trying to reject while at least one change is applied
            res = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "consoleme_admins@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertEqual(
                res.action_results[0].message,
                "Request cannot be rejected because at least one change has been applied already. "
                "Please apply or cancel the other changes.",
            )
            extended_request.changes.changes[0].status = Status.not_applied

            # Trying to cancel an approved request
            extended_request.request_status = RequestStatus.approved
            with pytest.raises(InvalidRequestParameter) as e:
                await parse_and_apply_policy_request_modification(
                    extended_request,
                    policy_request_model,
                    "consoleme_admins@example.com",
                    [],
                    last_updated,
                    tenant,
                )
                self.assertIn("cannot be rejected", str(e))

            # Rejecting valid request
            extended_request.request_status = RequestStatus.pending
            response = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "consoleme_admins@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertEqual(0, response.errors)
            # Make sure request got rejected
            self.assertEqual(RequestStatus.rejected, extended_request.request_status)

            policy_request_model.modification_model.command = (
                Command.move_back_to_pending
            )
            mock_move_back_to_pending.return_value = False
            # Trying to move back to pending request - not authorized
            with pytest.raises(Unauthorized) as e:
                await parse_and_apply_policy_request_modification(
                    extended_request,
                    policy_request_model,
                    "user2@example.com",
                    [],
                    last_updated,
                    tenant,
                )
                self.assertIn("Cannot move this request back to pending", str(e))

            mock_move_back_to_pending.return_value = True
            # Trying to move back to pending request - authorized
            response = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "consoleme_admins@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertEqual(0, response.errors)
            # Make sure request got moved back
            self.assertEqual(RequestStatus.pending, extended_request.request_status)

    @pytest.mark.skip(reason="EN-637")
    @pytest.mark.usefixtures("dynamodb")
    @pytest.mark.usefixtures("populate_caches")
    @patch("common.lib.v2.requests.send_communications_policy_change_request_v2")
    @patch(
        "common.lib.aws.fetch_iam_principal.fetch_iam_role",
    )
    @patch("common.lib.v2.requests.populate_old_policies")
    @patch("common.user_request.models.IAMRequest.write_v2")
    @patch("common.lib.v2.requests.can_admin_policies")
    @patch("common.lib.v2.requests.can_update_cancel_requests_v2")
    async def test_parse_and_apply_policy_request_modification_approve_request(
        self,
        mock_can_update_cancel_requests_v2,
        can_admin_policies,
        mock_dynamo_write,
        mock_populate_old_policies,
        mock_fetch_iam_role,
        mock_send_email,
    ):
        from common.config import config
        from common.exceptions.exceptions import Unauthorized
        from common.lib.asyncio import aio_wrapper
        from common.lib.redis import RedisHandler
        from common.lib.v2.requests import parse_and_apply_policy_request_modification

        # Redis is globally mocked. Let's store and retrieve a fake value
        red = RedisHandler().redis_sync(tenant)
        red.hmset(
            f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
            {
                "arn:aws:s3:::test_bucket": json.dumps({"accountId": "123456789013"}),
                "arn:aws:s3:::test_bucket_2": json.dumps({"accountId": "123456789013"}),
            },
        )

        s3_client = await aio_wrapper(
            boto3_cached_conn,
            "s3",
            tenant,
            None,
            service_type="client",
            future_expiration_minutes=15,
            account_number="123456789013",
            region="us-east-1",
            session_name="noq_unittest",
            arn_partition="aws",
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
        )
        s3_client.create_bucket(Bucket="test_bucket")

        extended_request = await get_extended_request_helper()
        resource_policy_change = {
            "principal": {
                "principal_arn": test_role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "resource_policy",
            "resources": [
                {
                    "arn": test_role_arn,
                    "name": test_role_name,
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "id": "123456",
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:s3:::test_bucket",
            "autogenerated": False,
            "supported": True,
            "policy": {
                "policy_document": {"Version": "2012-10-17", "Statement": []},
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )
        extended_request.changes.changes.append(resource_policy_change_model)
        updated_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:*"],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::test_bucket",
                        "arn:aws:s3:::test_bucket/abc/*",
                    ],
                    "Sid": "sid_test",
                }
            ],
        }
        input_body = {
            "modification_model": {
                "command": "update_change",
                "change_id": extended_request.changes.changes[0].id,
                "policy_document": updated_policy_doc,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = None
        mock_populate_old_policies.return_value = extended_request
        mock_fetch_iam_role.return_value = None
        mock_can_update_cancel_requests_v2.return_value = False
        can_admin_policies.return_value = False
        mock_send_email.return_value = None
        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )

        # Trying to approve while not being authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
                tenant,
            )
            self.assertIn("Unauthorized", str(e))

        can_admin_policies.return_value = True
        mock_can_update_cancel_requests_v2.return_value = True

        # Authorized person updating the change
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
            tenant,
        )

        # 0 errors for approving the request, which doesn't apply any resource policy changes
        self.assertEqual(0, response.errors)
        # Make sure inline policy change got updated in the request
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            updated_policy_doc,
        )
        self.assertEqual(extended_request.changes.changes[0].status, Status.not_applied)
        # Apply the change
        input_body = {
            "modification_model": {
                "command": "apply_change",
                "change_id": extended_request.changes.changes[0].id,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )

        await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
            tenant,
        )

        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)

        # Make sure this change got applied
        inline_policy = client.get_role_policy(
            RoleName=test_role_name,
            PolicyName=extended_request.changes.changes[0].policy_name,
        )
        self.assertEqual(
            extended_request.changes.changes[0].policy_name,
            inline_policy.get("PolicyName"),
        )
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )
        # Inline policy has been applied. Request should still be pending because
        # there's still a resource policy in the request
        self.assertEqual(RequestStatus.pending, extended_request.request_status)
        # Make sure resource policy change is still not applied
        self.assertEqual(extended_request.changes.changes[1].status, Status.not_applied)

        # Try to apply resource policy change. This should not work
        input_body = {
            "modification_model": {
                "command": "apply_change",
                "change_id": extended_request.changes.changes[1].id,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )

        # It fails when I try to add the patch as a decorator. Possibly due to the import in this method.
        with patch("smtplib.SMTP_SSL", autospec=True):
            response = await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "consoleme_admins@example.com",
                [],
                last_updated,
                tenant,
            )

        self.assertEqual(response.action_results[0].status, "success")
        self.assertEqual(
            response.action_results[0].message,
            "Successfully updated resource policy for arn:aws:s3:::test_bucket",
        )
        red.delete(f"{tenant}_AWSCONFIG_RESOURCE_CACHE")
        s3_client.delete_bucket(Bucket="test_bucket")


@pytest.mark.usefixtures("populate_caches")
class TestIsEligibleForAutoApproval(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.principal = AwsResourcePrincipalModel(
            principal_arn=role_arn,
            principal_type="AwsResource",
            account_id=role_arn.split(":")[4],
        )

        self.resource_tag_change = ResourceTagChangeModel(
            key="test",
            value="value",
            tag_action=TagAction.create,
            principal=self.principal,
            change_type="resource_tag",
        )

        self.tra_role_change = TraRoleChangeModel(
            principal=self.principal, change_type="tra_can_assume_role"
        )

        inline_policy_change = {
            "principal": {
                "principal_arn": role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": True,
            "action": "detach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                            ],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        self.inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        resource_policy_change = {
            "principal": {
                "principal_arn": role_arn,
                "principal_type": "AwsResource",
            },
            "change_type": "resource_policy",
            "resources": [
                {
                    "arn": role_arn,
                    "name": role_name,
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:s3:::test_bucket",
            "autogenerated": False,
            "policy": {
                "policy_document": {"Version": "2012-10-17", "Statement": []},
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        self.resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )

        self.extended_request = None

    def set_extended_request(self, *changes):
        self.extended_request = ExtendedRequestModel(
            id=str(randint(9999, 9999999)),
            principal=self.principal,
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=changes),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

    async def test_with_ineligible_change_types(self):
        self.set_extended_request(self.resource_tag_change)
        self.assertFalse(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

        self.set_extended_request(
            self.resource_tag_change, self.inline_policy_change_model
        )
        self.assertFalse(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

    async def test_with_resource_policy(self):
        # Can't auto approve with just a resource policy
        self.set_extended_request(self.resource_policy_change_model)
        self.assertFalse(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

        # However, auto approve is supported with inline policy + resource policy
        self.set_extended_request(
            self.resource_policy_change_model, self.inline_policy_change_model
        )
        self.assertTrue(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

    async def test_with_inline_policy(self):
        # auto approve is supported with inline policy
        self.set_extended_request(self.inline_policy_change_model)
        self.assertTrue(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

        # As well as inline policy + resource policy
        self.set_extended_request(
            self.resource_policy_change_model, self.inline_policy_change_model
        )
        self.assertTrue(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

        # As long as there are no ineligible changes
        self.set_extended_request(
            self.inline_policy_change_model, self.resource_tag_change
        )
        self.assertFalse(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

    async def test_with_tra(self):
        from common.config.config import CONFIG

        tra_config = await get_tra_config_for_request(tenant, role_arn, [])
        tra_config.enabled = True
        tra_config.requires_approval = True
        CONFIG.config["site_configs"][tenant][TRA_CONFIG_BASE_KEY] = tra_config.dict()

        # TRA request where requires_approval == True
        self.set_extended_request(self.tra_role_change)
        self.assertFalse(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

        # TRA requests where requires_approval == False
        tra_config.requires_approval = False
        CONFIG.config["site_configs"][tenant][TRA_CONFIG_BASE_KEY] = tra_config.dict()

        # Will be eligible for auto approval
        self.set_extended_request(self.tra_role_change)
        self.assertTrue(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )

        # As long as there are no ineligible changes
        self.set_extended_request(self.tra_role_change, self.resource_tag_change)
        self.assertFalse(
            await is_request_eligible_for_auto_approval(
                tenant, self.extended_request, "user@example.com", []
            )
        )
