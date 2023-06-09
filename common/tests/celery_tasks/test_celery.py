"""Docstring in public module."""
import copy
import json
import os
import sys
from unittest import TestCase
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync

from util.tests.fixtures.globals import tenant

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


@pytest.mark.usefixtures("aws_credentials")
@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("sts")
@pytest.mark.usefixtures("cloudtrail_table")
@pytest.mark.usefixtures("sqs")
@pytest.mark.usefixtures("sqs_queue")
@pytest.mark.usefixtures("iam")
@pytest.mark.usefixtures("dynamodb")
class TestCelerySync(TestCase):
    def setUp(self):
        from common.celery_tasks import celery_tasks as celery

        self.celery = celery

    @pytest.mark.skip(reason="EN-637")
    def cache_iam_resources_for_account(self):
        from common.aws.iam.role.models import IAMRole
        from common.config.config import CONFIG
        from common.lib.redis import RedisHandler

        red = RedisHandler().redis_sync(tenant)

        # Set the config value for the redis cache location
        old_config = copy.deepcopy(CONFIG.config)
        CONFIG.config = {
            **CONFIG.config,
            "aws": {
                **CONFIG.get_tenant_specific_key("aws", tenant, {}),
                "iamroles_redis_key": "cache_iam_resources_for_account",
            },
            "cache_iam_resources_across_accounts": {
                "all_roles_combined": {
                    "s3": {
                        "file": "cache_iam_resources_for_account.json.gz",
                    }
                }
            },
            "cloudtrail": {
                "enabled": True,
                "account_id": "123456789012",
                "queue_arn": "arn:aws:sqs:us-west-2:123456789012:noq-cloudtrail-access-denies",
            },
        }

        # Clear out the existing cache from Redis:
        red.delete("cache_iam_resources_for_account")
        # Run it:
        self.celery.cache_iam_resources_for_account("123456789012", tenant=tenant)

        # Verify that everything is there:
        results = async_to_sync(IAMRole.query)(tenant)

        remaining_roles = [
            "arn:aws:iam::123456789012:role/ConsoleMe",
            "arn:aws:iam::123456789012:role/cm_someuser_N",
            "arn:aws:iam::123456789012:role/awsaccount_user",
            "arn:aws:iam::123456789012:role/TestInstanceProfile",
            "arn:aws:iam::123456789012:role/rolename",
        ] + [f"arn:aws:iam::123456789012:role/RoleNumber{num}" for num in range(0, 10)]

        self.assertEqual(results["Count"], len(remaining_roles))
        self.assertEqual(results["Count"], red.hlen("cache_iam_resources_for_account"))

        for i in results["Items"]:
            remaining_roles.remove(i["arn"])
            self.assertEqual(i["accountId"], "123456789012")
            self.assertGreater(int(i["ttl"]), 0)
            self.assertIsNotNone(json.loads(i["policy"]))
            self.assertEqual(
                json.loads(
                    red.hget(f"{tenant}_cache_iam_resources_for_account", i["arn"])
                )["policy"],
                i["policy"],
            )

        # Should all be accounted for:
        self.assertEqual(remaining_roles, [])

        # We should have the same data in redis on all regions, this time coming from DDB
        old_conf_region = self.celery.config.region
        self.celery.config.region = "us-east-1"

        # Clear out the existing cache from Redis:
        red.delete("cache_iam_resources_for_account")

        # This should spin off extra fake celery tasks
        res = self.celery.cache_iam_resources_across_accounts(tenant)
        self.assertEqual(
            res,
            {
                "function": "common.celery_tasks.celery_tasks.cache_iam_resources_across_accounts",
                "cache_key": "cache_iam_resources_for_account",
                "num_roles": 15,
                "num_accounts": 1,
            },
        )  # This should spin off extra fake celery tasks
        res = self.celery.cache_iam_resources_across_accounts(tenant)
        self.assertEqual(
            res,
            {
                "function": "common.celery_tasks.celery_tasks.cache_iam_resources_across_accounts",
                "cache_key": "cache_iam_resources_for_account",
                "num_roles": 15,
                "num_accounts": 1,
            },
        )

        # Reset the config value:
        self.celery.config.region = old_conf_region
        CONFIG.config = old_config

    def test_trigger_credential_mapping_refresh_from_role_changes(self):
        res = self.celery.trigger_credential_mapping_refresh_from_role_changes(
            tenant=tenant
        )
        self.assertEqual(
            res,
            {
                "function": "common.celery_tasks.celery_tasks.trigger_credential_mapping_refresh_from_role_changes",
                "tenant": "example_com",
                "message": "Successfully checked role changes",
                "num_roles_changed": 2,
            },
        )

    def test_cache_cloudtrail_denies(self):
        from common.lib.aws.access_undenied.access_undenied_aws import (
            common,
            result_details,
        )
        from common.lib.aws.access_undenied.access_undenied_aws.results import (
            AnalysisResult,
        )

        with patch(
            "common.lib.aws.access_undenied.access_undenied_aws.simulate_custom_policy_helper.simulate_custom_policies",
            return_value=AnalysisResult(
                event_id="event_1234",
                assessment_result=common.AccessDeniedReason.IDENTITY_POLICY_EXPLICIT_DENY,
                result_details_=result_details.ExplicitDenyResultDetails(
                    policy_arn="aws:iam::123456789012:policy/role1",
                    policy_name="role1",
                    explicit_deny_policy_statement=json.dumps(
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
                    attachment_target_arn="arn:aws:iam::123456789012:role/role1",
                ),
            ),
        ):
            res = self.celery.cache_cloudtrail_denies(tenant)

        self.assertEqual(
            res,
            {
                "function": "common.celery_tasks.celery_tasks.cache_cloudtrail_denies",
                "tenant": tenant,
                "message": "Successfully cached cloudtrail denies",
                "num_new_cloudtrail_denies": 1,
                "num_cloudtrail_denies": 1,
            },
        )
