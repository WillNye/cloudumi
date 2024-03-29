import json
import re
from typing import Any, Optional

from aws_error_utils import ClientError, errors

import common.aws.iam.policy.utils
from common.config import config
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.aws.access_undenied.access_undenied_aws import (
    common,
    event_permission_data,
)
from common.models import SpokeAccount

logger = config.get_logger(__name__)


def _get_ecr_resource_policy(
    arn_match: re.Match,
    config: common.Config,
    region: str,
    resource: common.Resource,
) -> Optional[common.Policy]:
    cross_account_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", config.tenant)
        .with_query({"account_id": resource.account_id})
        .first.name
    )
    repository_policy_response = boto3_cached_conn(
        "ecr",
        config.tenant,
        None,
        region=region,
        account_number=resource.account_id,
        assume_role=cross_account_role_name,
        session_name="noq_get_ecr_policy",
    ).get_repository_policy(repositoryName=(arn_match.group("resource_id")))
    return common.Policy(
        attachment_target_arn=repository_policy_response["ARN"],
        attachment_target_type="Resource: ECR Repository",
        policy_name="ECRRepositoryResourcePolicy",
        policy_arn="/".join([resource.arn, "ECRRepositoryResourcePolicy"]),
        policy_document=repository_policy_response["ResourcePolicy"],
        policy_type=common.PolicyType.RESOURCE_POLICY,
    )


def _get_iam_resource_policy(
    config: common.Config, resource: common.Resource
) -> Optional[common.Policy]:
    cross_account_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", config.tenant)
        .with_query({"account_id": resource.account_id})
        .first.name
    )
    resource_policy_document = json.dumps(
        boto3_cached_conn(
            "iam",
            config.tenant,
            None,
            account_number=resource.account_id,
            assume_role=cross_account_role_name,
            session_name="noq_get_iam_resource_policy",
        ).get_role(RoleName=resource.arn.split("/")[-1])["Role"][
            "AssumeRolePolicyDocument"
        ]
    )
    return common.Policy(
        attachment_target_arn=resource.arn,
        attachment_target_type="Resource: IAM Role",
        policy_name="RoleTrustPolicy",
        policy_arn="/".join([resource.arn, "RoleTrustPolicy"]),
        policy_document=resource_policy_document,
        policy_type=common.PolicyType.RESOURCE_POLICY,
    )


def _get_kms_resource_policy(
    arn_match: re.Match,
    config: common.Config,
    region: str,
    resource: common.Resource,
) -> Optional[common.Policy]:
    cross_account_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", config.tenant)
        .with_query({"account_id": resource.account_id})
        .first.name
    )
    key_policy_document = boto3_cached_conn(
        "kms",
        config.tenant,
        None,
        region=region,
        account_number=resource.account_id,
        assume_role=cross_account_role_name,
        session_name="noq_get_kms_policy",
    ).get_key_policy(KeyId=(arn_match.group("resource_id")), PolicyName="default")[
        "Policy"
    ]
    return common.Policy(
        attachment_target_arn=resource.arn,
        attachment_target_type="Resource: KMS Key",
        policy_name="KMSKeyPolicy",
        policy_arn="/".join([resource.arn, "KMSKeyPolicy"]),
        policy_document=key_policy_document,
        policy_type=common.PolicyType.RESOURCE_POLICY,
    )


def _get_lambda_resource_policy(
    arn_match: re.Match,
    config: common.Config,
    region: str,
    resource: common.Resource,
) -> Optional[common.Policy]:
    lambda_function_policy_response = common.aws.iam.policy.utils.get_policy(
        FunctionName=(arn_match.group("resource_id"))
    )
    return common.Policy(
        attachment_target_arn=arn_match.group(0),
        attachment_target_type="Resource: Lambda Function",
        policy_name="LambdaFunctionResourcePolicy",
        policy_arn="/".join([resource.arn, "LambdaFunctionResourcePolicy"]),
        policy_document=lambda_function_policy_response["Policy"],
        policy_type=common.PolicyType.RESOURCE_POLICY,
    )


def _get_resource_account_session(
    config: common.Config, resource: common.Resource
) -> Any:
    if resource.account_id == config.account_id:
        return config.session
    cross_account_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", config.tenant)
        .with_query({"account_id": resource.account_id})
        .first.name
    )
    role_arn = f"arn:aws:iam::{resource.account_id}:role/{cross_account_role_name}"
    try:
        return boto3_cached_conn(
            "sts",
            config.tenant,
            None,
            account_number=resource.account_id,
            assume_role=cross_account_role_name,
            session_name="noq_get_account_session",
        )
    except ClientError as client_error:
        logger.error(
            f"Could not assume resource account role: {role_arn}:"
            f" {str(client_error)}"
        )
        raise common.AccessUndeniedError(
            f"[Error:{str(client_error)}] assuming [role_arn:{role_arn}] in the"
            f" resource account of [resource_arn={resource.arn}] when getting"
            " the resource policy.",
            common.AccessDeniedReason.ERROR,
        )


def _get_s3_resource_policy(
    arn_match: re.Match, config: common.Config, resource: common.Resource
) -> Optional[common.Policy]:
    bucket_name = arn_match.group("resource_type") or arn_match.group("resource_id")
    cross_account_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", config.tenant)
        .with_query({"account_id": resource.account_id})
        .first.name
    )
    s3_client = boto3_cached_conn(
        "s3",
        config.tenant,
        None,
        account_number=resource.account_id,
        assume_role=cross_account_role_name,
        session_name="noq_get_s3_resource_policy",
    )
    try:
        bucket_policy_document = s3_client.get_bucket_policy(Bucket=bucket_name)[
            "Policy"
        ]
    except (errors.NoSuchBucketPolicy, ClientError):
        bucket_policy_document = EMPTY_RESOURCE_POLICY.format(resource=resource.arn)
    return common.Policy(
        attachment_target_arn=resource.arn,
        attachment_target_type="Resource: S3 Bucket",
        policy_name="S3BucketPolicy",
        policy_arn="/".join([resource.arn, "S3BucketPolicy"]),
        policy_document=bucket_policy_document,
        policy_type=common.PolicyType.RESOURCE_POLICY,
    )


def _get_secretsmanager_resource_policy(
    arn_match: re.Match,
    config: common.Config,
    region: str,
    resource: common.Resource,
) -> Optional[common.Policy]:
    secret_policy_response = common.aws.iam.policy.utils.get_resource_policy(
        SecretId=(arn_match.group("resource_id"))
    )
    return common.Policy(
        attachment_target_arn=secret_policy_response["ARN"],
        attachment_target_type="Resource: SecretsManager Secret",
        policy_name="SecretResourcePolicy",
        policy_arn="/".join([resource.arn, "SecretResourcePolicy"]),
        policy_document=secret_policy_response["ResourcePolicy"],
        policy_type=common.PolicyType.RESOURCE_POLICY,
    )


def get_resource_policy(
    config: common.Config,
    event_permission_data_: event_permission_data.EventPermissionData,
    region: str,
) -> Optional[common.Policy]:
    if "*" in event_permission_data_.resource.arn:
        return None

    arn_match = re.search(
        common.RESOURCE_ARN_PATTERN,
        event_permission_data_.resource.arn,
        re.IGNORECASE,
    )
    if arn_match:
        service_name = arn_match.group("service")
    else:
        service_name = event_permission_data_.iam_permission.split(":")[0]
        if service_name != "secretsmanager":
            logger.warning(
                "Unable to parse service name from resource"
                f" [resource:{event_permission_data_.resource.arn}]"
                " ignoring resource policy..."
            )
            return None
    try:
        if service_name == "iam" and event_permission_data_.iam_permission in [
            "AssumeRole",
            "AssumeRoleWithSAML",
            "AssumeRoleWithWebIdentity",
        ]:
            return _get_iam_resource_policy(config, event_permission_data_.resource)
        if service_name == "s3":
            return _get_s3_resource_policy(
                arn_match,
                config,
                event_permission_data_.resource,
            )
        if service_name == "kms" and arn_match.group("resource_type") == "key":
            return _get_kms_resource_policy(
                arn_match,
                config,
                region,
                event_permission_data_.resource,
            )
        if service_name == "secretsmanager":
            return _get_secretsmanager_resource_policy(
                arn_match,
                config,
                region,
                event_permission_data_.resource,
            )
        if service_name == "ecr":
            return _get_ecr_resource_policy(
                arn_match,
                config,
                region,
                event_permission_data_.resource,
            )
        if service_name == "lambda":
            return _get_lambda_resource_policy(
                arn_match,
                config,
                region,
                event_permission_data_.resource,
            )
    except ClientError as client_error:
        raise common.AccessUndeniedError(
            f"[Error:{str(client_error)}] Getting resource policy for"
            f" [resource_arn={event_permission_data_.resource.arn}]",
            common.AccessDeniedReason.ERROR,
        )
    logger.warning(
        f"Service [service_name:{service_name}] does not have resource policy"
        " support in AccessUndenied, ignoring resource policy..."
    )
    return None


EMPTY_RESOURCE_POLICY = """
  {{
    "Version": "2012-10-17",
    "Statement": [
      {{
        "Effect": "Allow",
        "NotPrincipal": "*",
        "NotAction": "*",
        "Resource": "{resource}"
      }}
    ]
  }}
"""
