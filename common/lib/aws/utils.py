import asyncio
import fnmatch
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import boto3
import sentry_sdk
from botocore.exceptions import ClientError

from common.aws.iam.policy.utils import (
    fetch_managed_policy_details,
    get_resource_policy,
    should_exclude_policy_from_comparison,
)
from common.aws.iam.role.config import get_active_tear_users_tag
from common.aws.utils import ResourceSummary, get_resource_tag
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import (
    BackgroundCheckNotPassedException,
    InvalidInvocationArgument,
    MissingConfigurationValue,
)
from common.lib import noq_json as ujson
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.account_indexers.aws_organizations import (
    retrieve_org_structure,
    retrieve_scps_for_organization,
)
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.s3 import (
    get_bucket_location,
    get_bucket_policy,
    get_bucket_resource,
    get_bucket_tagging,
)
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.sns import get_topic_attributes
from common.lib.aws.sqs import get_queue_attributes, get_queue_url, list_queue_tags
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import redis_hgetex, redis_hsetex
from common.models import (
    ExtendedRequestModel,
    HubAccount,
    OrgAccount,
    RequestStatus,
    ServiceControlPolicyArrayModel,
    ServiceControlPolicyModel,
    SpokeAccount,
    Status,
)
from common.user_request.models import IAMRequest

log = config.get_logger(__name__)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()

PERMISSIONS_SEPARATOR = "||"


async def fetch_resource_details(
    account_id: str,
    service: str,
    resource_name: str,
    region: str,
    tenant,
    user,
    path: str = None,
) -> dict:
    if service == "s3":
        return await fetch_s3_bucket(account_id, resource_name, tenant, user)
    elif service == "sqs":
        return await fetch_sqs_queue(account_id, region, resource_name, tenant, user)
    elif service == "sns":
        return await fetch_sns_topic(account_id, region, resource_name, tenant, user)
    elif service == "managed_policy":
        return await fetch_managed_policy_details(
            account_id, resource_name, tenant, user, path
        )
    else:
        return {}


async def fetch_sns_topic(
    account_id: str, region: str, resource_name: str, tenant: str, user: str
) -> dict:
    from common.lib.policies import get_aws_config_history_url_for_resource

    regions = await get_enabled_regions_for_account(account_id, tenant)
    if region not in regions:
        raise InvalidInvocationArgument(
            f"Region '{region}' is not valid region on account '{account_id}'."
        )

    arn: str = f"arn:aws:sns:{region}:{account_id}:{resource_name}"
    client = await aio_wrapper(
        boto3_cached_conn,
        "sns",
        tenant,
        user,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        retry_max_attempts=2,
        session_name="noq_fetch_sns_topic",
    )

    result: Dict = await aio_wrapper(
        get_topic_attributes,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        TopicArn=arn,
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        retry_max_attempts=2,
        tenant=tenant,
        user=user,
    )

    tags: Dict = await aio_wrapper(client.list_tags_for_resource, ResourceArn=arn)
    result["TagSet"] = tags["Tags"]
    if not isinstance(result["Policy"], dict):
        result["Policy"] = json.loads(result["Policy"])

    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        arn,
        resource_name,
        "AWS::SNS::Topic",
        tenant,
        region=region,
    )
    return result


async def fetch_sqs_queue(
    account_id: str, region: str, resource_name: str, tenant: str, user: str
) -> dict:
    from common.lib.policies import get_aws_config_history_url_for_resource

    regions = await get_enabled_regions_for_account(account_id, tenant)
    if region not in regions:
        raise InvalidInvocationArgument(
            f"Region '{region}' is not valid region on account '{account_id}'."
        )

    queue_url: str = await aio_wrapper(
        get_queue_url,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        QueueName=resource_name,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        retry_max_attempts=2,
        tenant=tenant,
        user=user,
    )

    result: Dict = await aio_wrapper(
        get_queue_attributes,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        QueueUrl=queue_url,
        AttributeNames=["All"],
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        retry_max_attempts=2,
        tenant=tenant,
        user=user,
    )

    tags: Dict = await aio_wrapper(
        list_queue_tags,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        QueueUrl=queue_url,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        retry_max_attempts=2,
        tenant=tenant,
        user=user,
    )
    result["TagSet"]: list = []
    result["QueueUrl"]: str = queue_url
    if tags:
        result["TagSet"] = [{"Key": k, "Value": v} for k, v in tags.items()]
    if result.get("CreatedTimestamp"):
        result["created_time"] = datetime.utcfromtimestamp(
            int(float(result["CreatedTimestamp"]))
        ).isoformat()
    if result.get("LastModifiedTimestamp"):
        result["updated_time"] = datetime.utcfromtimestamp(
            int(float(result["LastModifiedTimestamp"]))
        ).isoformat()
    # Unfortunately, the queue_url we get from our `get_queue_url` call above doesn't match the ID of the queue in
    # AWS Config, so we must hack our own.
    queue_url_manual = (
        f"https://sqs.{region}.amazonaws.com/{account_id}/{resource_name}"
    )
    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        queue_url_manual,
        resource_name,
        "AWS::SQS::Queue",
        tenant,
        region=region,
    )
    return result


async def get_bucket_location_with_fallback(
    bucket_name: str, account_id: str, tenant, fallback_region: str = "us-east-1"
) -> str:
    try:
        bucket_location_res = await aio_wrapper(
            get_bucket_location,
            Bucket=bucket_name,
            account_number=account_id,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            retry_max_attempts=2,
            tenant=tenant,
        )
        bucket_location = bucket_location_res.get("LocationConstraint", fallback_region)
        if not bucket_location:
            # API get_bucket_location returns None for buckets in us-east-1
            bucket_location = "us-east-1"
        if bucket_location == "EU":
            bucket_location = "eu-west-1"
        if bucket_location == "US":
            bucket_location = "us-east-1"
    except ClientError:
        bucket_location = fallback_region
        sentry_sdk.capture_exception()
    return bucket_location


async def fetch_s3_bucket(
    account_id: str, bucket_name: str, tenant: str, user: str
) -> dict:
    """Fetch S3 Bucket and applicable policies

    :param account_id:
    :param bucket_name:
    :return:
    """

    from common.lib.policies import get_aws_config_history_url_for_resource

    log_data: Dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "bucket_name": bucket_name,
        "account_id": account_id,
    }
    log.debug(log_data)
    created_time = None
    bucket_location = "us-east-1"

    try:
        bucket_resource = await aio_wrapper(
            get_bucket_resource,
            bucket_name,
            account_number=account_id,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            retry_max_attempts=2,
            tenant=tenant,
            user=user,
        )
        created_time_stamp = bucket_resource.creation_date
        if created_time_stamp:
            created_time = created_time_stamp.isoformat()
    except ClientError:
        sentry_sdk.capture_exception()
    try:
        bucket_location = await get_bucket_location_with_fallback(
            bucket_name, account_id, tenant
        )
        policy: Dict = await aio_wrapper(
            get_bucket_policy,
            account_number=account_id,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name,
            region=bucket_location,
            Bucket=bucket_name,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            retry_max_attempts=2,
            tenant=tenant,
            user=user,
        )
    except ClientError as e:
        if "NoSuchBucketPolicy" in str(e):
            policy = {"Policy": "{}"}
        else:
            raise
    try:
        tags: Dict = await aio_wrapper(
            get_bucket_tagging,
            account_number=account_id,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name,
            region=bucket_location,
            Bucket=bucket_name,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            retry_max_attempts=2,
            tenant=tenant,
            user=user,
        )
    except ClientError as e:
        if "NoSuchTagSet" in str(e):
            tags = {"TagSet": []}
        else:
            raise

    result: Dict = {**policy, **tags, "created_time": created_time}
    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        bucket_name,
        bucket_name,
        "AWS::S3::Bucket",
        tenant,
        region=bucket_location,
    )
    result["Policy"] = json.loads(result["Policy"])

    return result


async def raise_if_background_check_required_and_no_background_check(
    role, user, tenant
):
    auth = get_plugin_by_name(
        config.get_tenant_specific_key("plugins.auth", tenant, "cmsaas_auth")
    )()
    for compliance_account_id in config.get_tenant_specific_key(
        "aws.compliance_account_ids", tenant, []
    ):
        if compliance_account_id == role.split(":")[4]:
            user_info = await auth.get_user_info(user, object=True)
            if not user_info.passed_background_check:
                function = f"{__name__}.{sys._getframe().f_code.co_name}"
                log_data: dict = {
                    "function": function,
                    "user": user,
                    "role": role,
                    "message": "User trying to access SEG role without background check",
                }
                log.error(log_data)
                stats.count(
                    f"{function}.access_denied_background_check_not_passed",
                    tags={
                        "function": function,
                        "user": user,
                        "role": role,
                        "tenant": tenant,
                    },
                )
                raise BackgroundCheckNotPassedException(
                    config.get_tenant_specific_key(
                        "aws.background_check_not_passed",
                        tenant,
                        "You must have passed a background check to access role "
                        "{role}.",
                    ).format(role=role)
                )


async def delete_iam_user(account_id, iam_user_name, username, tenant: str) -> bool:
    """
    This function assumes the user has already been pre-authorized to delete an IAM user. it will detach all managed
    policies, delete all inline policies, delete all access keys, and finally delete the IAM user.

    :param account_id: Account ID that the IAM user is on
    :param iam_user_name: name of IAM user to delete
    :param username: actor's username
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to delete role",
        "account_id": account_id,
        "iam_user_name": iam_user_name,
        "user": username,
    }
    log.info(log_data)
    iam_user = await fetch_iam_user_details(account_id, iam_user_name, tenant, username)

    # Detach managed policies
    for policy in await aio_wrapper(iam_user.attached_policies.all):
        await aio_wrapper(policy.load)
        log.info(
            {
                **log_data,
                "message": "Detaching managed policy from user",
                "policy_arn": policy.arn,
            }
        )
        await aio_wrapper(policy.detach_user, UserName=iam_user)

    # Delete Inline policies
    for policy in await aio_wrapper(iam_user.policies.all):
        await aio_wrapper(policy.load)
        log.info(
            {
                **log_data,
                "message": "Deleting inline policy on user",
                "policy_name": policy.name,
            }
        )
        await aio_wrapper(policy.delete)

    log.info({**log_data, "message": "Performing access key deletion"})
    access_keys = iam_user.access_keys.all()
    for access_key in access_keys:
        access_key.delete()

    log.info({**log_data, "message": "Performing user deletion"})
    await aio_wrapper(iam_user.delete)
    stats.count(
        f"{log_data['function']}.success",
        tags={
            "iam_user_name": iam_user_name,
            "tenant": tenant,
        },
    )
    return True


async def prune_iam_resource_tag(
    boto_conn, resource_type: str, resource_id: str, tag: str, value: str = None
):
    """Removes a subset of a tag or the entire tag from a supported IAM resource"""
    assert resource_type in ["role", "user", "policy"]

    if resource_type == "policy":
        boto_kwargs = {"PolicyArn": resource_id}
    else:
        boto_kwargs = {f"{resource_type.title()}Name": resource_id}

    if not value:
        await aio_wrapper(
            getattr(boto_conn, f"untag_{resource_type}"), TagKeys=[tag], **boto_kwargs
        )

    resource_tags = await aio_wrapper(
        getattr(boto_conn, f"list_{resource_type}_tags"), **boto_kwargs
    )
    resource_tag = get_resource_tag(resource_tags, tag, True, set())
    resource_tag.remove(value)

    if resource_tag:
        await aio_wrapper(
            getattr(boto_conn, f"tag_{resource_type}"),
            Tags=[{"Key": tag, "Value": ":".join(resource_tag)}],
            **boto_kwargs,
        )
    else:
        await aio_wrapper(
            getattr(boto_conn, f"untag_{resource_type}"), TagKeys=[tag], **boto_kwargs
        )


async def fetch_iam_user_details(account_id, iam_user_name, tenant, user):
    """
    Fetches details about an IAM user from AWS. If spoke_accounts configuration
    is set, the hub (central) account role will assume the
    configured role to perform the action.

    :param account_id: account ID
    :param iam_user_name: IAM user name
    :return: iam_user resource
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to fetch role details",
        "account": account_id,
        "iam_user_name": iam_user_name,
        "tenant": tenant,
    }
    log.info(log_data)
    iam_resource = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        tenant,
        user,
        service_type="resource",
        account_number=account_id,
        region=config.region,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        session_name=sanitize_session_name("noq_fetch_iam_user_details"),
        retry_max_attempts=2,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
    )
    try:
        iam_user = await aio_wrapper(iam_resource.User, iam_user_name)
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "NoSuchEntity":
            log_data["message"] = "Requested user doesn't exist"
            log.error(log_data)
        raise
    await aio_wrapper(iam_user.load)
    return iam_user


async def get_enabled_regions_for_account(account_id: str, tenant: str) -> Set[str]:
    """
    Returns a list of regions enabled for an account based on an EC2 Describe Regions call. Can be overridden with a
    global configuration of static regions (Configuration key: `celery.sync_regions`), or a configuration of specific
    regions per account (Configuration key:  `get_enabled_regions_for_account.{account_id}`)
    """
    enabled_regions_for_account = config.get_tenant_specific_key(
        f"get_enabled_regions_for_account.{account_id}", tenant
    )
    if enabled_regions_for_account:
        return enabled_regions_for_account

    celery_sync_regions = config.get_tenant_specific_key(
        "celery.sync_regions", tenant, []
    )
    if celery_sync_regions:
        return celery_sync_regions

    client = await aio_wrapper(
        boto3_cached_conn,
        "ec2",
        tenant,
        None,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        read_only=True,
        retry_max_attempts=2,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        session_name="noq_get_enabled_regions",
    )

    regions = await aio_wrapper(client.describe_regions)
    return {r["RegionName"] for r in regions["Regions"]}


async def get_all_scps(
    tenant: str, force_sync=False
) -> Dict[str, List[ServiceControlPolicyModel]]:
    """Retrieve a dictionary containing all Service Control Policies across organizations

    Args:
        force_sync: force a cache update
    """
    redis_key = config.get_tenant_specific_key(
        "cache_scps_across_organizations.redis.key.all_scps_key",
        tenant,
        f"{tenant}_ALL_AWS_SCPS",
    )
    scps = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        s3_bucket=config.get_tenant_specific_key(
            "cache_scps_across_organizations.s3.bucket", tenant
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_scps_across_organizations.s3.file",
            tenant,
            "scps/cache_scps_v1.json.gz",
        ),
        default={},
        max_age=86400,
        tenant=tenant,
    )
    if force_sync or not scps:
        scps = await cache_all_scps(tenant)
    scp_models = {}
    for account, org_scps in scps.items():
        scp_models[account] = [ServiceControlPolicyModel(**scp) for scp in org_scps]
    return scp_models


async def cache_all_scps(tenant) -> Dict[str, Any]:
    """Store a dictionary of all Service Control Policies across organizations in the cache"""
    all_scps = {}
    for organization in (
        ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ):
        org_account_id = organization.account_id
        role_to_assume = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": org_account_id})
            .first.name
        )

        if not org_account_id:
            raise MissingConfigurationValue(
                "Your AWS Organizations Master Account ID is not specified in configuration. "
                "Unable to sync accounts from "
                "AWS Organizations"
            )

        if not role_to_assume:
            raise MissingConfigurationValue(
                "Noq doesn't know what role to assume to retrieve account information "
                "from AWS Organizations. please set the appropriate configuration value."
            )
        org_scps = await retrieve_scps_for_organization(
            org_account_id, tenant, role_to_assume=role_to_assume, region=config.region
        )
        all_scps[org_account_id] = org_scps
    redis_key = config.get_tenant_specific_key(
        "cache_scps_across_organizations.redis.key.all_scps_key",
        tenant,
        f"{tenant}_ALL_AWS_SCPS",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "cache_scps_across_organizations.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "cache_scps_across_organizations.s3.file",
            tenant,
            "scps/cache_scps_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        all_scps, redis_key=redis_key, s3_bucket=s3_bucket, s3_key=s3_key, tenant=tenant
    )
    return all_scps


async def get_org_structure(tenant, force_sync=False) -> Dict[str, Any]:
    """Retrieve a dictionary containing the organization structure

    Args:
        force_sync: force a cache update
    """
    redis_key = config.get_tenant_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        tenant,
        f"{tenant}_AWS_ORG_STRUCTURE",
    )
    org_structure = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        s3_bucket=config.get_tenant_specific_key(
            "cache_organization_structure.s3.bucket", tenant
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_organization_structure.s3.file",
            tenant,
            "scps/cache_org_structure_v1.json.gz",
        ),
        default={},
        tenant=tenant,
    )
    if force_sync or not org_structure:
        org_structure = await cache_org_structure(tenant)
    return org_structure


async def onboard_new_accounts_from_orgs(tenant: str) -> list[str]:
    log_data = {"function": "onboard_new_accounts_from_orgs", "tenant": tenant}
    new_accounts_onboarded = []
    org_accounts = ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    for org_account in org_accounts:
        if not org_account.automatically_onboard_accounts or not org_account.role_names:
            continue

        spoke_role_name = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": org_account.account_id})
            .first.name
        )

        org_client = boto3_cached_conn(
            "organizations",
            tenant,
            None,
            account_number=org_account.account_id,
            assume_role=spoke_role_name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            session_name=sanitize_session_name("noq_autodiscover_aws_org_accounts"),
            read_only=True,
        )

        try:
            paginator = org_client.get_paginator("list_accounts")
            for page in paginator.paginate():
                for account in page.get("Accounts"):
                    log_data["account_id"] = account["Id"]
                    try:
                        (
                            ModelAdapter(SpokeAccount)
                            .load_config("spoke_accounts", tenant)
                            .with_query({"account_id": account["Id"]})
                            .first.name
                        )
                        continue  # We already know about this account, and can skip it
                    except ValueError as e:
                        if "did not find any items with the given query" not in str(e):
                            raise
                        # We don't yet know about this account, and can process it.

                    for aws_organizations_role_name in org_account.role_names:
                        # Get STS client on Org Account
                        # attempt sts:AssumeRole
                        org_role_arn = f"arn:aws:iam::{account['Id']}:role/{aws_organizations_role_name}"
                        log_data["org_role_arn"] = "org_role_arn"
                        try:
                            # TODO: SpokeRoles, by default, do not have the ability to assume other roles
                            # To automatically onboard a new account, we have to grant the Spoke role this capability
                            # temporarily then wait for the permission to propagate. THIS NEEDS TO BE DOCUMENTED
                            # and we need a finally statement to ensure we attempt to remove it.
                            # TODO: Inject retry and/or sleep
                            # TODO: Save somewhere that we know we attempted this account before, so no need to try again.
                            org_sts_client = boto3_cached_conn(
                                "sts",
                                tenant,
                                None,
                                region=config.region,
                                assume_role=spoke_role_name,
                                account_number=org_account.account_id,
                                session_name="noq_onboard_new_accounts_from_orgs",
                            )

                            # Use the spoke role on the org management account to assume into the org role on the
                            # new (unknown) account
                            new_account_credentials = await aio_wrapper(
                                org_sts_client.assume_role,
                                RoleArn=org_role_arn,
                                RoleSessionName="noq_onboard_new_accounts_from_orgs",
                            )

                            new_account_cf_client = await aio_wrapper(
                                boto3.client,
                                "cloudformation",
                                aws_access_key_id=new_account_credentials[
                                    "Credentials"
                                ]["AccessKeyId"],
                                aws_secret_access_key=new_account_credentials[
                                    "Credentials"
                                ]["SecretAccessKey"],
                                aws_session_token=new_account_credentials[
                                    "Credentials"
                                ]["SessionToken"],
                                region_name=config.region,
                            )

                            # Onboard the account.
                            spoke_stack_name = config.get(
                                "_global_.integrations.aws.spoke_role_name",
                                "NoqSpokeRole",
                            )
                            spoke_role_template_url = config.get(
                                "_global_.integrations.aws.registration_spoke_role_cf_template",
                                "https://s3.us-east-1.amazonaws.com/cloudumi-cf-templates/cloudumi_spoke_role.yaml",
                            )
                            spoke_roles = (
                                ModelAdapter(SpokeAccount)
                                .load_config("spoke_accounts", tenant)
                                .models
                            )
                            external_id = config.get_tenant_specific_key(
                                "tenant_details.external_id", tenant
                            )
                            if not external_id:
                                log.error(
                                    {**log_data, "error": "External ID not found"}
                                )
                                continue
                            cluster_role = config.get(
                                "_global_.integrations.aws.node_role"
                            )
                            if not cluster_role:
                                log.error(
                                    {**log_data, "error": "Cluster role not found"}
                                )
                                continue
                            if spoke_roles:
                                spoke_role_name = spoke_roles[0].name
                                spoke_stack_name = spoke_role_name
                            else:
                                spoke_role_name = config.get(
                                    "_global_.integrations.aws.spoke_role_name",
                                    "NoqSpokeRole",
                                )
                            hub_account = (
                                ModelAdapter(HubAccount)
                                .load_config("hub_account", tenant)
                                .model
                            )
                            customer_central_account_role = hub_account.role_arn

                            region = config.get(
                                "_global_.integrations.aws.region", "us-west-2"
                            )
                            account_id = config.get(
                                "_global_.integrations.aws.account_id"
                            )
                            cluster_id = config.get("_global_.deployment.cluster_id")
                            registration_topic_arn = config.get(
                                "_global_.integrations.aws.registration_topic_arn",
                                f"arn:aws:sns:{region}:{account_id}:{cluster_id}-registration-topic",
                            )
                            spoke_role_parameters = [
                                {
                                    "ParameterKey": "ExternalIDParameter",
                                    "ParameterValue": external_id,
                                },
                                {
                                    "ParameterKey": "CentralRoleArnParameter",
                                    "ParameterValue": customer_central_account_role,
                                },
                                {
                                    "ParameterKey": "HostParameter",
                                    "ParameterValue": tenant,
                                },
                                {
                                    "ParameterKey": "SpokeRoleNameParameter",
                                    "ParameterValue": spoke_role_name,
                                },
                                {
                                    "ParameterKey": "RegistrationTopicArnParameter",
                                    "ParameterValue": registration_topic_arn,
                                },
                            ]
                            response = new_account_cf_client.create_stack(
                                StackName=spoke_stack_name,
                                TemplateURL=spoke_role_template_url,
                                Parameters=spoke_role_parameters,
                                Capabilities=[
                                    "CAPABILITY_NAMED_IAM",
                                ],
                            )
                            log.debug(
                                {
                                    **log_data,
                                    "stack_id": response["StackId"],
                                }
                            )
                            new_accounts_onboarded.append(account["Id"])
                            break
                        except Exception as e:
                            log.error({**log_data, "error": str(e)}, exc_info=True)
        except Exception as e:
            log.error(f"Unable to retrieve roles from AWS Organizations: {e}")
    return new_accounts_onboarded


async def sync_account_names_from_orgs(tenant: str) -> dict[str, str]:
    log_data = {"function": "sync_account_names_from_orgs", "tenant": tenant}
    org_account_id_to_name = {}
    account_names_synced = {}
    accounts_d: Dict[str, str] = await get_account_id_to_name_mapping(tenant)
    org_account_ids = [
        org.account_id
        for org in ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ]
    for org_account_id in org_account_ids:
        spoke_account = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": org_account_id})
            .first
        )
        if not spoke_account:
            continue
        org_client = boto3_cached_conn(
            "organizations",
            tenant,
            None,
            account_number=org_account_id,
            assume_role=spoke_account.name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            session_name=sanitize_session_name("noq_autodiscover_aws_org_accounts"),
            read_only=True,
        )
        try:
            paginator = org_client.get_paginator("list_accounts")
            for page in paginator.paginate():
                for account in page.get("Accounts", []):
                    org_account_id_to_name[account["Id"]] = account["Name"]
        except Exception as e:
            log.error({**log_data, "error": str(e)}, exc_info=True)
        for account_id, account_name in accounts_d.items():
            if (
                account_id != account_name
            ):  # The account name was changed from the account ID, don't override it.
                continue  # TODO: Maybe remove this condition?
            if account_id not in org_account_id_to_name:
                continue
            spoke_account_to_replace = (
                ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", tenant)
                .with_query({"account_id": account_id})
                .first
            )
            spoke_account_to_replace.account_name = org_account_id_to_name[account_id]
            await ModelAdapter(SpokeAccount).load_config(
                "spoke_accounts", tenant
            ).from_dict(spoke_account_to_replace).with_object_key(
                ["account_id"]
            ).store_item_in_list()
            account_names_synced[account_id] = spoke_account_to_replace.account_name
    return account_names_synced


async def autodiscover_aws_org_accounts(tenant: str) -> set[str]:
    """
    This branch automatically discovers AWS Organization Accounts from Spoke Accounts. It filters out accounts that are
    already flagged as AWS Organization Management Accounts. It also filters out accounts that we've already checked.
    """
    org_accounts_added = set()
    accounts_d: Dict[str, str] = await get_account_id_to_name_mapping(tenant)
    org_account_ids = [
        org.account_id
        for org in ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ]
    for account_id in accounts_d.keys():
        if account_id in org_account_ids:
            continue
        spoke_account = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first
        )
        if not spoke_account:
            continue
        if spoke_account.org_access_checked:
            continue
        org = boto3_cached_conn(
            "organizations",
            tenant,
            None,
            account_number=account_id,
            assume_role=spoke_account.name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            session_name=sanitize_session_name("noq_autodiscover_aws_org_accounts"),
            read_only=True,
        )
        org_details = None
        org_account_name = None
        org_management_account = False
        try:
            org_details = org.describe_organization()
            if (
                org_details
                and org_details["Organization"]["MasterAccountId"] == account_id
            ):
                org_management_account = True
                spoke_account.org_management_account = org_management_account
                account_details = org.describe_account(AccountId=account_id)
                if account_details:
                    org_account_name = account_details["Account"]["Name"]
        except Exception as e:
            log.error(
                "Unable to retrieve roles from AWS Organizations: {}".format(e),
                exc_info=True,
            )
        spoke_account.org_access_checked = True
        await ModelAdapter(SpokeAccount).load_config(
            "spoke_accounts", tenant
        ).from_dict(spoke_account.dict()).with_object_key(
            ["account_id"]
        ).store_item_in_list()
        if org_management_account and org_details:
            await ModelAdapter(OrgAccount).load_config(
                "org_accounts", tenant
            ).from_dict(
                {
                    "org_id": org_details["Organization"]["Id"],
                    "account_id": account_id,
                    "account_name": org_account_name,
                    "owner": org_details["Organization"]["MasterAccountEmail"],
                }
            ).with_object_key(
                ["org_id"]
            ).store_item_in_list()
            org_accounts_added.add(account_id)
    return org_accounts_added


async def cache_org_structure(tenant: str) -> Dict[str, Any]:
    """Store a dictionary of the organization structure in the cache"""
    all_org_structure = {}
    for organization in (
        ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ):
        org_account_id = organization.account_id
        role_to_assume = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": org_account_id})
            .first.name
        )
        if not org_account_id:
            raise MissingConfigurationValue(
                "Your AWS Organizations Master Account ID is not specified in configuration. "
                "Unable to sync accounts from "
                "AWS Organizations"
            )

        if not role_to_assume:
            raise MissingConfigurationValue(
                "Noq doesn't know what role to assume to retrieve account information "
                "from AWS Organizations. please set the appropriate configuration value."
            )
        org_structure = await retrieve_org_structure(
            org_account_id, tenant, role_to_assume=role_to_assume, region=config.region
        )
        all_org_structure.update(org_structure)
    redis_key = config.get_tenant_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        tenant,
        f"{tenant}_AWS_ORG_STRUCTURE",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "cache_organization_structure.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "cache_organization_structure.s3.file",
            tenant,
            "scps/cache_org_structure_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        all_org_structure,
        redis_key=redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        tenant=tenant,
    )
    return all_org_structure


async def _is_member_of_ou(
    identifier: str, ou: Dict[str, Any]
) -> Tuple[bool, Set[str]]:
    """Recursively walk org structure to determine if the account or OU is in the org and, if so, return all OUs of which the account or OU is a member

    Args:
        identifier: AWS account or OU ID
        ou: dictionary representing the organization/organizational unit structure to search
    """
    found = False
    ou_path = set()
    for child in ou.get("Children", []):
        if child.get("Id") == identifier:
            found = True
        elif child.get("Type") == "ORGANIZATIONAL_UNIT":
            found, ou_path = await _is_member_of_ou(identifier, child)
        if found:
            ou_path.add(ou.get("Id"))
            break
    return found, ou_path


async def get_organizational_units_for_account(
    identifier: str,
    tenant: str,
) -> Set[str]:
    """Return a set of Organizational Unit IDs for a given account or OU ID

    Args:
        identifier: AWS account or OU ID
    """
    all_orgs = await get_org_structure(tenant)
    organizational_units = set()
    for org_id, org_structure in all_orgs.items():
        found, organizational_units = await _is_member_of_ou(identifier, org_structure)
        if found:
            break
    if not organizational_units:
        log.warning("could not find account in organization")
    return organizational_units


async def _scp_targets_account_or_ou(
    scp: ServiceControlPolicyModel, identifier: str, organizational_units: Set[str]
) -> bool:
    """Return True if the provided SCP targets the account or OU identifier provided

    Args:
        scp: Service Control Policy whose targets we check
        identifier: AWS account or OU ID
        organizational_units: set of IDs for OUs of which the identifier is a member
    """
    for target in scp.targets:
        if target.target_id == identifier or target.target_id in organizational_units:
            return True
    return False


async def get_scps_for_account_or_ou(
    identifier: str, tenant: str
) -> ServiceControlPolicyArrayModel:
    """Retrieve a list of Service Control Policies for the account or OU specified by the identifier

    Args:
        identifier: AWS account or OU ID
    """
    all_scps = await get_all_scps(tenant)
    account_ous = await get_organizational_units_for_account(identifier, tenant)
    scps_for_account = []
    for org_account_id, scps in all_scps.items():
        # Iterate through each org's SCPs and see if the provided account_id is in the targets
        for scp in scps:
            if await _scp_targets_account_or_ou(scp, identifier, account_ous):
                scps_for_account.append(scp)
    scps = ServiceControlPolicyArrayModel(__root__=scps_for_account)
    return scps


def allowed_to_sync_role(
    role_arn: str,
    role_tags: List[Optional[Dict[str, str]]],
    tenant: str,
) -> bool:
    """
    This function determines whether Noq is allowed to sync or otherwise manipulate an IAM role. By default,
    Noq will sync all roles that it can get its grubby little hands on. However, Noq administrators can tell
    Noq to only sync roles with either 1) Specific ARNs, or 2) Specific tag key/value pairs. All configured tags
    must exist on the role for Noq to sync it.

    Here's an example configuration for a tag-based restriction:

    ```
    roles:
      allowed_tags:
        tag1: value1
        tag2: value2
    ```

    And another one for an ARN-based restriction:

    ```
    roles:
      allowed_arns:
        - arn:aws:iam::111111111111:role/role-name-here-1
        - arn:aws:iam::111111111111:role/role-name-here-2
        - arn:aws:iam::111111111111:role/role-name-here-3
        - arn:aws:iam::222222222222:role/role-name-here-1
        - arn:aws:iam::333333333333:role/role-name-here-1
    ```

    :param
        arn: The AWS role arn
        role_tags: A dictionary of role tags

    :return: boolean specifying whether Noq is allowed to sync / access the role
    """
    allowed_tags = config.get_tenant_specific_key("roles.allowed_tags", tenant, {})
    allowed_arns = config.get_tenant_specific_key("roles.allowed_arns", tenant, [])
    if not allowed_tags and not allowed_arns:
        return True

    if role_arn in allowed_arns:
        return True

    # Convert list of role tag dicts to a single key/value dict of tags
    # ex:
    # role_tags = [{'Key': 'noq-authorized', 'Value': 'noq_admins'},
    # {'Key': 'Description', 'Value': 'Noq OSS Demo Role'}]
    # so: actual_tags = {'noq-authorized': 'noq_admins', 'Description': 'Noq OSS Demo Role'}
    actual_tags = {
        d["Key"]: d["Value"] for d in role_tags
    }  # Convert List[Dicts] to 1 Dict

    # All configured allowed_tags must exist in the role's actual_tags for this condition to pass
    if allowed_tags and allowed_tags.items() <= actual_tags.items():
        return True
    return False


async def remove_expired_request_changes(
    extended_request: ExtendedRequestModel,
    tenant: str,
    user: Optional[str],
    force_refresh: bool = False,
) -> None:
    """
    If this feature is enabled, it will look at changes and remove those that are expired policies if they have been.
    Changes can be designated as temporary by defining an expiration date.
    In the future, we may allow specifying temporary policies by `Sid` or other means.
    """
    from common.aws.iam.role.models import IAMRole
    from common.lib.v2.aws_principals import get_role_details

    should_update_policy_request = False
    current_dateint = datetime.today().strftime("%Y%m%d")
    if (
        not extended_request.expiration_date
        or str(extended_request.expiration_date) > current_dateint
    ):
        return

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to expire policy",
        "policy_request_id": extended_request.id,
    }
    log.debug(log_data)

    for change in extended_request.changes.changes:
        if change.status != Status.applied:
            continue

        principal_arn = change.principal.principal_arn
        if change.change_type in [
            "managed_policy_resource",
            "resource_policy",
            "sts_resource_policy",
        ]:
            principal_arn = change.arn

        try:
            resource_summary = await ResourceSummary.set(tenant, principal_arn)
        except ValueError:
            # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
            # we can't revoke this change
            log_data["message"] = "Resource account not found"
            log.warning(log_data)
            continue

        # resource name is none for s3 buckets
        principal_name = resource_summary.name
        resource_service = resource_summary.service
        resource_type = resource_summary.resource_type
        resource_region = resource_summary.region
        resource_account = resource_summary.account

        client = await aio_wrapper(
            boto3_cached_conn,
            resource_service,
            tenant,
            user,
            service_type="client",
            future_expiration_minutes=15,
            account_number=resource_account,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": resource_account})
            .first.name,
            region=resource_region or config.region,
            session_name=sanitize_session_name("noq_revoke_expired_policies"),
            arn_partition="aws",
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            retry_max_attempts=2,
        )

        if change.change_type == "inline_policy":
            try:
                if resource_type == "role":
                    await aio_wrapper(
                        client.delete_role_policy,
                        RoleName=principal_name,
                        PolicyName=change.policy_name,
                    )
                elif resource_type == "user":
                    await aio_wrapper(
                        client.delete_user_policy,
                        UserName=principal_name,
                        PolicyName=change.policy_name,
                    )
                change.status = Status.expired
                should_update_policy_request = True

            except client.exceptions.NoSuchEntityException:
                log_data["message"] = "Policy was not found"
                log_data[
                    "error"
                ] = f"{change.policy_name} was not attached to {resource_type}"
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

                change.status = Status.expired
                should_update_policy_request = True

            except Exception as e:
                log_data["message"] = "Exception occurred deleting inline policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

        elif change.change_type == "permissions_boundary":
            try:
                if resource_type == "role":
                    await aio_wrapper(
                        client.delete_role_permissions_boundary,
                        RoleName=principal_name,
                    )
                elif resource_type == "user":
                    await aio_wrapper(
                        client.delete_user_permissions_boundary,
                        UserName=principal_name,
                    )
                change.status = Status.expired
                should_update_policy_request = True

            except client.exceptions.NoSuchEntityException:
                log_data["message"] = "Policy was not found"
                log_data[
                    "error"
                ] = f"permission boundary was not attached to {resource_type}"
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

                change.status = Status.expired
                should_update_policy_request = True

            except Exception as e:
                log_data[
                    "message"
                ] = "Exception occurred detaching permissions boundary"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

        elif change.change_type == "managed_policy":
            try:
                if resource_type == "role":
                    await aio_wrapper(
                        client.detach_role_policy,
                        RoleName=principal_name,
                        PolicyArn=change.arn,
                    )
                elif resource_type == "user":
                    await aio_wrapper(
                        client.detach_user_policy,
                        UserName=principal_name,
                        PolicyArn=change.arn,
                    )
                change.status = Status.expired
                should_update_policy_request = True

            except client.exceptions.NoSuchEntityException:
                log_data["message"] = "Policy was not found"
                log_data["error"] = f"{change.arn} was not attached to {resource_type}"
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

                change.status = Status.expired
                should_update_policy_request = True

            except Exception as e:
                log_data["message"] = "Exception occurred detaching managed policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

        elif change.change_type == "resource_tag":
            try:
                await prune_iam_resource_tag(
                    client, resource_type, principal_name, change.key, change.value
                )
                change.status = Status.expired
                should_update_policy_request = True
                force_refresh = True

            except client.exceptions.NoSuchEntityException:
                log_data["message"] = "Policy was not found"
                log_data["error"] = f"{change.key} was not attached to {resource_type}"
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

                change.status = Status.expired
                should_update_policy_request = True

            except KeyError:
                log_data["message"] = "Value not found for key"
                log_data["error"] = f"{change.key} does not contain {change.value}"
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

                change.status = Status.expired
                should_update_policy_request = True

            except Exception as e:
                log_data["message"] = "Exception occurred deleting tag"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

        elif change.change_type == "tear_can_assume_role":
            request_user = extended_request.requester_info.extended_info.get(
                "userName", None
            )

            try:
                await prune_iam_resource_tag(
                    client,
                    "role",
                    principal_name,
                    get_active_tear_users_tag(tenant),
                    request_user,
                )
                change.status = Status.expired
                should_update_policy_request = True
                force_refresh = True

            except client.exceptions.NoSuchEntityException:
                log_data["message"] = "Role not found"
                log_data["error"] = f"Role not found: {principal_name}"
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

                change.status = Status.expired
                should_update_policy_request = True

            except KeyError:
                log_data["message"] = "TEAR support not active for user"
                log_data["error"] = f"TEAR support not active for {request_user}"
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

                change.status = Status.expired
                should_update_policy_request = True

            except Exception as e:
                log_data["message"] = "Exception occurred deleting tag"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

        elif (
            change.change_type == "resource_policy"
            or change.change_type == "sts_resource_policy"
        ):
            try:
                new_policy_statement = []

                if change.change_type == "resource_policy":

                    existing_policy = await get_resource_policy(
                        resource_account,
                        resource_service,
                        resource_type,
                        resource_region,
                        tenant,
                        user,
                    )

                elif change.change_type == "sts_resource_policy":
                    role = await get_role_details(
                        resource_account,
                        principal_name,
                        tenant,
                        extended=True,
                        force_refresh=force_refresh,
                    )
                    if not role:
                        log.error(
                            {
                                **log_data,
                                "message": (
                                    "Unable to retrieve role. Won't attempt to remove cross-account policy."
                                ),
                            }
                        )
                        return
                    existing_policy = role.assume_role_policy_document

                for statement in existing_policy.get("Statement", []):
                    if str(extended_request.expiration_date) in statement.get(
                        "Sid", ""
                    ):
                        continue
                    new_policy_statement.append(statement)

                existing_policy["Statement"] = new_policy_statement

                if resource_service == "s3":
                    if len(new_policy_statement) == 0:
                        await aio_wrapper(
                            client.delete_bucket_policy,
                            Bucket=resource_type,
                            ExpectedBucketOwner=resource_account,
                        )
                    else:
                        await aio_wrapper(
                            client.put_bucket_policy,
                            Bucket=resource_type,
                            Policy=ujson.dumps(existing_policy),
                        )
                elif resource_service == "sns":
                    await aio_wrapper(
                        client.set_topic_attributes,
                        TopicArn=change.arn,
                        AttributeName="Policy",
                        AttributeValue=ujson.dumps(existing_policy),
                    )
                elif resource_service == "sqs":
                    queue_url: dict = await aio_wrapper(
                        client.get_queue_url, QueueName=resource_type
                    )

                    if len(new_policy_statement) == 0:
                        await aio_wrapper(
                            client.set_queue_attributes,
                            QueueUrl=queue_url.get("QueueUrl"),
                            Attributes={"Policy": ""},
                        )

                    else:
                        await aio_wrapper(
                            client.set_queue_attributes,
                            QueueUrl=queue_url.get("QueueUrl"),
                            Attributes={"Policy": ujson.dumps(existing_policy)},
                        )
                elif resource_service == "iam":
                    await aio_wrapper(
                        client.update_assume_role_policy,
                        RoleName=principal_name,
                        PolicyDocument=ujson.dumps(existing_policy),
                    )

                change.status = Status.expired
                should_update_policy_request = True

            except Exception as e:
                log_data["message"] = "Exception occurred updating resource policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()

    if should_update_policy_request:
        try:
            extended_request.request_status = RequestStatus.expired
            await IAMRequest.write_v2(extended_request, tenant)

            if resource_type == "role":
                await IAMRole.get(
                    tenant,
                    resource_account,
                    principal_arn,
                    force_refresh=force_refresh,
                    run_sync=True,
                )

            elif resource_type == "user":
                from common.aws.iam.user.utils import fetch_iam_user

                await fetch_iam_user(
                    resource_account,
                    principal_arn,
                    tenant,
                    force_refresh=force_refresh,
                    run_sync=True,
                )

        except Exception as e:
            log_data["message"] = "Exception unable to update policy status to expired"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()


async def remove_expired_tenant_requests(tenant: str):
    all_requests = await IAMRequest.query(
        tenant, filter_condition=(IAMRequest.status == "approved")
    )

    for request in all_requests:
        await remove_expired_request_changes(
            ExtendedRequestModel.parse_obj(request.extended_request.dict()),
            tenant,
            None,
        )

    # Can swap back to this once it's thread safe
    # await asyncio.gather(*[
    #     remove_expired_request_changes(ExtendedRequestModel.parse_obj(request["extended_request"]), tenant, None)
    #     for request in all_policy_requests
    # ])


async def remove_expired_requests_for_tenants(tenants: list[str]) -> dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    await asyncio.gather(
        *[remove_expired_tenant_requests(tenant) for tenant in tenants]
    )

    return log_data


def get_aws_principal_owner(role_details: Dict[str, Any], tenant: str) -> Optional[str]:
    """
    Identifies the owning user/group of an AWS principal based on one or more trusted and configurable principal tags.
    `owner` is used to notify application owners of permission problems with their detected AWS principals or resources
    if another identifier (ie: session name) for a principal doesn't point to a specific user for notification.

    :return: owner: str
    """
    owner = None
    owner_tag_names = config.get_tenant_specific_key("aws.tags.owner", tenant, [])
    if not owner_tag_names:
        return owner
    if isinstance(owner_tag_names, str):
        owner_tag_names = [owner_tag_names]
    role_tags = role_details.get("Tags")
    for owner_tag_name in owner_tag_names:
        for role_tag in role_tags:
            if role_tag["Key"] == owner_tag_name:
                return role_tag["Value"]
    return owner


async def simulate_iam_principal_action(
    principal_arn,
    action,
    resource_arn,
    source_ip,
    tenant,
    user,
    expiration_seconds: Optional[int] = None,
):
    """
    Simulates an IAM principal action affecting a resource

    :return:
    """
    if not expiration_seconds:
        expiration_seconds = (
            config.get_tenant_specific_key(
                "aws.simulate_iam_principal_action.expiration_seconds",
                tenant,
                3600,
            ),
        )
    # simulating IAM principal policies is expensive.
    # Temporarily cache and return results by principal_arn, action, and resource_arn. We don't consider source_ip
    # when caching because it could vary greatly for application roles running on multiple instances/containers.
    resource_arn_exists_temp_matches_redis_key: str = config.get_tenant_specific_key(
        "resource_arn_known_in_aws_config.redis.temp_matches_key",
        tenant,
        f"{tenant}_TEMP_POLICY_SIMULATION_CACHE",
    )

    cache_key = f"{principal_arn}-{action}-{resource_arn}"
    result = await redis_hgetex(
        resource_arn_exists_temp_matches_redis_key, cache_key, tenant
    )
    if result:
        return result

    ip_regex = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    context_entries = []
    if source_ip and re.match(ip_regex, source_ip):
        context_entries.append(
            {
                "ContextKeyName": "aws:SourceIp",
                "ContextKeyValues": [source_ip],
                "ContextKeyType": "ip",
            }
        )
    account_id = principal_arn.split(":")[4]
    client = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        tenant,
        user,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        retry_max_attempts=2,
        session_name="noq_simulate_principal_action",
    )
    try:
        response = await aio_wrapper(
            client.simulate_principal_policy,
            PolicySourceArn=principal_arn,
            ActionNames=[
                action,
            ],
            ResourceArns=[
                resource_arn,
            ],
            # TODO: Attach resource policy when discoverable
            # ResourcePolicy='string',
            # TODO: Attach Account ID of resource
            # ResourceOwner='string',
            ContextEntries=context_entries,
            MaxItems=100,
        )

        await redis_hsetex(
            resource_arn_exists_temp_matches_redis_key,
            resource_arn,
            response["EvaluationResults"],
            expiration_seconds,
            tenant,
        )
    except Exception:
        sentry_sdk.capture_exception()
        return None
    return response["EvaluationResults"]


async def entry_in_entries(value: str, values_to_compare: List[str]) -> bool:
    """Returns True if value is included in values_to_compare, using wildcard matching.

    :param value: Some string. Usually a resource or IAM action. IE: s3:getbucketpolicy
    :param values_to_compare: A list of strings, usually resources or actions. IE: ['s3:*', 's3:ListBucket']
    :return: a boolean that specifies whether value is encommpassed in values_to_compare
    """
    for compare_to in values_to_compare:
        if value == compare_to:
            return True
        if compare_to == "*":
            return True
        if "*" not in compare_to and ":" in value and ":" in compare_to:
            if compare_to.split(":")[0] != value.split(":")[0]:
                continue
        if fnmatch.fnmatch(value, compare_to):
            return True
    return False


async def includes_resources(resourceA: List[str], resourceB: List[str]) -> bool:
    """Returns True if all of the resources in resourceA are included in resourceB, using fnmatch (wildcard) matching.

    :param resourceA: A list of resource ARNs. For example: ['arn:aws:s3:::my-bucket/*', 'arn:aws:s3:::my-bucket/my-object']
    :param resourceB: Another list of resource ARNs. For example: ['*']
    :return: True if all of the resources in resourceA are included/encompassed in resourceB, otherwise False.
    """
    for resource in resourceA:
        match = False
        if await entry_in_entries(resource, resourceB):
            match = True
        if not match:
            return False
    return True


async def is_already_allowed_by_other_policy(
    inline_policy: Dict[str, Any], all_policies: List[Dict[str, Any]]
) -> bool:
    """Returns True if a list of policies (all_policies) has permissions that already encompass inline_policy.

    A caveat: This function will ignore comparing equivalent policies. eg: If inline_policy matches a policy in all_policies, it
    will be ignored and this function will continue comparing the inline_policy against all of the other policies in
    all_policies. Why? Because normally we're comparing a single inline policy against a list of inline policies which
    includes all policies (including the current)

    :param inline_policy: A specific policy statement, ie: {'Action': ['s3:putbuckettagging'], 'Effect': 'Allow', 'Resource': ['*']}
    :param all_policies: A list of policy documents to compare `inline_policy` to. IE: [{'Action': ['s3:putbuckettagging'], 'Effect': 'Allow', 'Resource': ['*']}, ...]
    :raises Exception: Validation error if the policy is not supported for comparison.
    :return: A boolean, whether the `inline_policy` is already allowed by a policy in the list of `all_policies`.
    """
    if await should_exclude_policy_from_comparison(inline_policy):
        return False
    if not isinstance(inline_policy["Resource"], list) or not isinstance(
        inline_policy["Action"], list
    ):
        raise Exception("Please normalize actions and resources into lists first")
    for compare_policy in all_policies:
        if compare_policy == inline_policy:
            continue
        if await should_exclude_policy_from_comparison(compare_policy):
            continue
        if not isinstance(compare_policy["Resource"], list) or not isinstance(
            compare_policy["Action"], list
        ):
            raise Exception("Please normalize actions and resources into lists first")
        if not await includes_resources(
            inline_policy["Resource"], compare_policy["Resource"]
        ):
            continue
        for action in inline_policy["Action"]:
            if not await entry_in_entries(action, compare_policy["Action"]):
                continue
            return True
    return False
