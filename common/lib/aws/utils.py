import asyncio
import copy
import fnmatch
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import pytz
import sentry_sdk
import ujson
from botocore.exceptions import ClientError, ParamValidationError
from dateutil.parser import parse
from deepdiff import DeepDiff
from parliament import analyze_policy_string, enhance_finding
from policy_sentry.util.arns import get_account_from_arn, parse_arn

from common.aws.iam.role.models import IAMRole
from common.aws.iam.user.utils import fetch_iam_user
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import (
    BackgroundCheckNotPassedException,
    InvalidInvocationArgument,
    MissingConfigurationValue,
)
from common.lib.account_indexers.aws_organizations import (
    retrieve_org_structure,
    retrieve_scps_for_organization,
)
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.aws_config import query
from common.lib.aws.iam import (
    get_active_tear_users_tag,
    get_managed_policy_document,
    get_policy,
)
from common.lib.aws.s3 import (
    get_bucket_location,
    get_bucket_policy,
    get_bucket_resource,
    get_bucket_tagging,
)
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.session import get_session_for_tenant
from common.lib.aws.sns import get_topic_attributes
from common.lib.aws.sqs import get_queue_attributes, get_queue_url, list_queue_tags
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.generic import sort_dict
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler, redis_hget, redis_hgetex, redis_hsetex
from common.lib.tenants import get_all_hosts
from common.models import (
    ExtendedRequestModel,
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


async def get_resource_policy(
    account: str, resource_type: str, name: str, region: str, host: str, user: str
):
    try:
        details = await fetch_resource_details(
            account, resource_type, name, region, host, user
        )
    except ClientError:
        # We don't have access to this resource, so we can't get the policy.
        details = {}

    # Default policy
    default_policy = {"Version": "2012-10-17", "Statement": []}

    # When NoSuchBucketPolicy, the above method returns {"Policy": {}}, so we default to blank policy
    if "Policy" in details and "Statement" not in details["Policy"]:
        details = {"Policy": default_policy}

    # Default to a blank policy
    return details.get("Policy", default_policy)


async def get_resource_policies(
    principal_arn: str,
    resource_actions: Dict[str, Dict[str, Any]],
    account: str,
    host: str,
) -> Tuple[List[Dict], bool]:
    resource_policies: List[Dict] = []
    cross_account_request: bool = False
    for resource_name, resource_info in resource_actions.items():
        resource_account: str = resource_info.get("account", "")
        if resource_account and resource_account != account:
            # This is a cross-account request. Might need a resource policy.
            cross_account_request = True
            resource_type: str = resource_info.get("type", "")
            resource_region: str = resource_info.get("region", "")
            old_policy = await get_resource_policy(
                resource_account,
                resource_type,
                resource_name,
                resource_region,
                host,
                None,
            )
            arns = resource_info.get("arns", [])
            actions = resource_info.get("actions", [])
            new_policy = await generate_updated_resource_policy(
                old_policy, principal_arn, arns, actions, ""
            )

            result = {
                "resource": resource_name,
                "account": resource_account,
                "type": resource_type,
                "region": resource_region,
                "policy_document": new_policy,
            }
            resource_policies.append(result)

    return resource_policies, cross_account_request


async def generate_updated_resource_policy(
    existing: Dict,
    principal_arn: str,
    resource_arns: List[str],
    actions: List[str],
    policy_sid: str,
    include_resources: bool = True,
) -> Dict:
    """

    :param existing: Dict: the current existing policy document
    :param principal_arn: the Principal ARN which wants access to the resource
    :param resource_arns: the Resource ARNs
    :param actions: The list of Actions to be added
    :param include_resources: whether to include resources in the new statement or not
    :return: Dict: generated updated resource policy that includes a new statement for the listed actions
    """
    policy_dict = deepcopy(existing)
    new_statement = {
        "Effect": "Allow",
        "Principal": {"AWS": [principal_arn]},
        "Action": list(set(actions)),
        "Sid": policy_sid,
    }
    if include_resources:
        new_statement["Resource"] = resource_arns
    policy_dict["Statement"].append(new_statement)
    return policy_dict


async def fetch_resource_details(
    account_id: str,
    resource_type: str,
    resource_name: str,
    region: str,
    host,
    user,
    path: str = None,
) -> dict:
    if resource_type == "s3":
        return await fetch_s3_bucket(account_id, resource_name, host, user)
    elif resource_type == "sqs":
        return await fetch_sqs_queue(account_id, region, resource_name, host, user)
    elif resource_type == "sns":
        return await fetch_sns_topic(account_id, region, resource_name, host, user)
    elif resource_type == "managed_policy":
        return await fetch_managed_policy_details(
            account_id, resource_name, path, host, user
        )
    else:
        return {}


async def fetch_managed_policy_details(
    account_id: str, resource_name: str, host: str, user: str, path: str = None
) -> Optional[Dict]:
    from common.lib.policies import get_aws_config_history_url_for_resource

    if not host:
        raise Exception("host not configured")
    if path:
        resource_name = path + "/" + resource_name
    policy_arn: str = f"arn:aws:iam::{account_id}:policy/{resource_name}"
    result: Dict = {}
    result["Policy"] = await aio_wrapper(
        get_managed_policy_document,
        policy_arn=policy_arn,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        host=host,
        user=user,
    )
    policy_details = await aio_wrapper(
        get_policy,
        policy_arn=policy_arn,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        host=host,
        user=user,
    )

    try:
        result["TagSet"] = policy_details["Policy"]["Tags"]
    except KeyError:
        result["TagSet"] = []
    result["config_timeline_url"] = await get_aws_config_history_url_for_resource(
        account_id,
        policy_arn,
        resource_name,
        "AWS::IAM::ManagedPolicy",
        host,
        region=config.region,
    )

    return result


async def fetch_sns_topic(
    account_id: str, region: str, resource_name: str, host: str, user: str
) -> dict:
    from common.lib.policies import get_aws_config_history_url_for_resource

    regions = await get_enabled_regions_for_account(account_id, host)
    if region not in regions:
        raise InvalidInvocationArgument(
            f"Region '{region}' is not valid region on account '{account_id}'."
        )

    arn: str = f"arn:aws:sns:{region}:{account_id}:{resource_name}"
    client = await aio_wrapper(
        boto3_cached_conn,
        "sns",
        host,
        user,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        retry_max_attempts=2,
    )

    result: Dict = await aio_wrapper(
        get_topic_attributes,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        TopicArn=arn,
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        retry_max_attempts=2,
        host=host,
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
        host,
        region=region,
    )
    return result


async def fetch_sqs_queue(
    account_id: str, region: str, resource_name: str, host: str, user: str
) -> dict:
    from common.lib.policies import get_aws_config_history_url_for_resource

    regions = await get_enabled_regions_for_account(account_id, host)
    if region not in regions:
        raise InvalidInvocationArgument(
            f"Region '{region}' is not valid region on account '{account_id}'."
        )

    queue_url: str = await aio_wrapper(
        get_queue_url,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        QueueName=resource_name,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        retry_max_attempts=2,
        host=host,
        user=user,
    )

    result: Dict = await aio_wrapper(
        get_queue_attributes,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        QueueUrl=queue_url,
        AttributeNames=["All"],
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        retry_max_attempts=2,
        host=host,
        user=user,
    )

    tags: Dict = await aio_wrapper(
        list_queue_tags,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        QueueUrl=queue_url,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        retry_max_attempts=2,
        host=host,
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
        host,
        region=region,
    )
    return result


async def get_bucket_location_with_fallback(
    bucket_name: str, account_id: str, host, fallback_region: str = "us-east-1"
) -> str:
    try:
        bucket_location_res = await aio_wrapper(
            get_bucket_location,
            Bucket=bucket_name,
            account_number=account_id,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first.name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            retry_max_attempts=2,
            host=host,
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
    account_id: str, bucket_name: str, host: str, user: str
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
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first.name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            retry_max_attempts=2,
            host=host,
            user=user,
        )
        created_time_stamp = bucket_resource.creation_date
        if created_time_stamp:
            created_time = created_time_stamp.isoformat()
    except ClientError:
        sentry_sdk.capture_exception()
    try:
        bucket_location = await get_bucket_location_with_fallback(
            bucket_name, account_id, host
        )
        policy: Dict = await aio_wrapper(
            get_bucket_policy,
            account_number=account_id,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first.name,
            region=bucket_location,
            Bucket=bucket_name,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            retry_max_attempts=2,
            host=host,
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
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first.name,
            region=bucket_location,
            Bucket=bucket_name,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            retry_max_attempts=2,
            host=host,
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
        host,
        region=bucket_location,
    )
    result["Policy"] = json.loads(result["Policy"])

    return result


async def raise_if_background_check_required_and_no_background_check(role, user, host):
    auth = get_plugin_by_name(
        config.get_host_specific_key("plugins.auth", host, "cmsaas_auth")
    )()
    for compliance_account_id in config.get_host_specific_key(
        "aws.compliance_account_ids", host, []
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
                        "host": host,
                    },
                )
                raise BackgroundCheckNotPassedException(
                    config.get_host_specific_key(
                        "aws.background_check_not_passed",
                        host,
                        "You must have passed a background check to access role "
                        "{role}.",
                    ).format(role=role)
                )


async def delete_iam_user(account_id, iam_user_name, username, host: str) -> bool:
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
    iam_user = await fetch_iam_user_details(account_id, iam_user_name, host, username)

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
            "host": host,
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
    resource_tag = get_role_tag(resource_tags, tag, True, set())
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


async def fetch_iam_user_details(account_id, iam_user_name, host, user):
    """
    Fetches details about an IAM user from AWS. If spoke_accounts configuration
    is set, the hub (central) account ConsoleMeInstanceProfile role will assume the
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
        "host": host,
    }
    log.info(log_data)
    iam_resource = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        host,
        user,
        service_type="resource",
        account_number=account_id,
        region=config.region,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        session_name=sanitize_session_name("fetch_iam_user_details"),
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
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


def get_role_tag(
    role: Dict, key: str, is_list: Optional[bool] = False, default: Optional[any] = None
) -> any:
    """
    Retrieves and parses the value of a provided AWS tag.
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param key: key of the tag
    :param is_list: The value for the key is a list type
    :param default: Default value is tag not found
    :return:
    """
    for tag in role.get("Tags", role.get("tags", [])):
        if tag.get("Key") == key:
            val = tag.get("Value")
            if is_list:
                return set([] if not val else val.split(":"))
            return val
    return default


def role_has_managed_policy(role: Dict, managed_policy_name: str) -> bool:
    """
    Checks a role dictionary to determine if a managed policy is attached
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param managed_policy_name: the name of the managed policy
    :return:
    """

    for managed_policy in role.get("AttachedManagedPolicies", []):
        if managed_policy.get("PolicyName") == managed_policy_name:
            return True
    return False


def role_newer_than_x_days(role: Dict, days: int) -> bool:
    """
    Checks a role dictionary to determine if it is newer than the specified number of days
    :param role:  An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param days: number of days
    :return:
    """
    if isinstance(role.get("CreateDate"), str):
        role["CreateDate"] = parse(role.get("CreateDate"))
    role_age = datetime.now(tz=pytz.utc) - role.get("CreateDate")
    if role_age.days < days:
        return True
    return False


def is_role_instance_profile(role: Dict) -> bool:
    """
    Checks a role naively to determine if it is associate with an instance profile.
    We only check by name, and not the actual attached instance profiles.
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :return:
    """
    return role.get("RoleName").endswith("InstanceProfile")


def get_region_from_arn(arn):
    """Given an ARN, return the region in the ARN, if it is available. In certain cases like S3 it is not"""
    result = parse_arn(arn)
    # Support S3 buckets with no values under region
    if result["region"] is None:
        result = ""
    else:
        result = result["region"]
    return result


def get_resource_from_arn(arn):
    """Given an ARN, parse it according to ARN namespacing and return the resource. See
    http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html for more details on ARN namespacing.
    """
    result = parse_arn(arn)
    return result["resource"]


def get_service_from_arn(arn):
    """Given an ARN string, return the service"""
    result = parse_arn(arn)
    return result["service"]


async def get_enabled_regions_for_account(account_id: str, host: str) -> Set[str]:
    """
    Returns a list of regions enabled for an account based on an EC2 Describe Regions call. Can be overridden with a
    global configuration of static regions (Configuration key: `celery.sync_regions`), or a configuration of specific
    regions per account (Configuration key:  `get_enabled_regions_for_account.{account_id}`)
    """
    enabled_regions_for_account = config.get_host_specific_key(
        f"get_enabled_regions_for_account.{account_id}", host
    )
    if enabled_regions_for_account:
        return enabled_regions_for_account

    celery_sync_regions = config.get_host_specific_key("celery.sync_regions", host, [])
    if celery_sync_regions:
        return celery_sync_regions

    client = await aio_wrapper(
        boto3_cached_conn,
        "ec2",
        host,
        None,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        read_only=True,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )

    regions = await aio_wrapper(client.describe_regions)
    return {r["RegionName"] for r in regions["Regions"]}


async def access_analyzer_validate_policy(
    policy: str, log_data, host, policy_type: str = "IDENTITY_POLICY"
) -> List[Dict[str, Any]]:
    session = get_session_for_tenant(host)
    try:
        enhanced_findings = []
        client = await aio_wrapper(
            session.client,
            "accessanalyzer",
            region_name=config.region,
            **config.get_host_specific_key("boto3.client_kwargs", host, {}),
        )
        access_analyzer_response = await aio_wrapper(
            client.validate_policy,
            policyDocument=policy,
            policyType=policy_type,  # ConsoleMe only supports identity policy analysis currently
        )
        for finding in access_analyzer_response.get("findings", []):
            for location in finding.get("locations", []):
                enhanced_findings.append(
                    {
                        "issue": finding.get("issueCode"),
                        "detail": "",
                        "location": {
                            "line": location.get("span", {})
                            .get("start", {})
                            .get("line"),
                            "column": location.get("span", {})
                            .get("start", {})
                            .get("column"),
                            "filepath": None,
                        },
                        "severity": finding.get("findingType"),
                        "title": finding.get("issueCode"),
                        "description": finding.get("findingDetails"),
                    }
                )
        return enhanced_findings
    except (ParamValidationError, ClientError) as e:
        log.error(
            {
                **log_data,
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Error retrieving Access Analyzer data",
                "policy": policy,
                "error": str(e),
            }
        )
        sentry_sdk.capture_exception()
        return []


async def parliament_validate_iam_policy(policy: str) -> List[Dict[str, Any]]:
    analyzed_policy = await aio_wrapper(analyze_policy_string, policy)
    findings = analyzed_policy.findings

    enhanced_findings = []

    for finding in findings:
        enhanced_finding = await aio_wrapper(enhance_finding, finding)
        enhanced_findings.append(
            {
                "issue": enhanced_finding.issue,
                "detail": json.dumps(enhanced_finding.detail),
                "location": enhanced_finding.location,
                "severity": enhanced_finding.severity,
                "title": enhanced_finding.title,
                "description": enhanced_finding.description,
            }
        )
    return enhanced_findings


async def validate_iam_policy(policy: str, log_data: Dict, host: str):
    parliament_findings: List = await parliament_validate_iam_policy(policy)
    access_analyzer_findings: List = await access_analyzer_validate_policy(
        policy, log_data, host, policy_type="IDENTITY_POLICY"
    )
    return parliament_findings + access_analyzer_findings


async def get_all_scps(
    host: str, force_sync=False
) -> Dict[str, List[ServiceControlPolicyModel]]:
    """Retrieve a dictionary containing all Service Control Policies across organizations

    Args:
        force_sync: force a cache update
    """
    redis_key = config.get_host_specific_key(
        "cache_scps_across_organizations.redis.key.all_scps_key",
        host,
        f"{host}_ALL_AWS_SCPS",
    )
    scps = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        s3_bucket=config.get_host_specific_key(
            "cache_scps_across_organizations.s3.bucket", host
        ),
        s3_key=config.get_host_specific_key(
            "cache_scps_across_organizations.s3.file",
            host,
            "scps/cache_scps_v1.json.gz",
        ),
        default={},
        max_age=86400,
        host=host,
    )
    if force_sync or not scps:
        scps = await cache_all_scps(host)
    scp_models = {}
    for account, org_scps in scps.items():
        scp_models[account] = [ServiceControlPolicyModel(**scp) for scp in org_scps]
    return scp_models


async def cache_all_scps(host) -> Dict[str, Any]:
    """Store a dictionary of all Service Control Policies across organizations in the cache"""
    all_scps = {}
    for organization in (
        ModelAdapter(OrgAccount).load_config("org_accounts", host).models
    ):
        org_account_id = organization.account_id
        role_to_assume = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
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
            org_account_id, host, role_to_assume=role_to_assume, region=config.region
        )
        all_scps[org_account_id] = org_scps
    redis_key = config.get_host_specific_key(
        "cache_scps_across_organizations.redis.key.all_scps_key",
        host,
        f"{host}_ALL_AWS_SCPS",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get_host_specific_key(
        "celery.active_region", host, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_host_specific_key(
            "cache_scps_across_organizations.s3.bucket", host
        )
        s3_key = config.get_host_specific_key(
            "cache_scps_across_organizations.s3.file",
            host,
            "scps/cache_scps_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        all_scps, redis_key=redis_key, s3_bucket=s3_bucket, s3_key=s3_key, host=host
    )
    return all_scps


async def get_org_structure(host, force_sync=False) -> Dict[str, Any]:
    """Retrieve a dictionary containing the organization structure

    Args:
        force_sync: force a cache update
    """
    redis_key = config.get_host_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        host,
        f"{host}_AWS_ORG_STRUCTURE",
    )
    org_structure = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        s3_bucket=config.get_host_specific_key(
            "cache_organization_structure.s3.bucket", host
        ),
        s3_key=config.get_host_specific_key(
            "cache_organization_structure.s3.file",
            host,
            "scps/cache_org_structure_v1.json.gz",
        ),
        default={},
        host=host,
    )
    if force_sync or not org_structure:
        org_structure = await cache_org_structure(host)
    return org_structure


async def cache_org_structure(host: str) -> Dict[str, Any]:
    """Store a dictionary of the organization structure in the cache"""
    all_org_structure = {}
    for organization in (
        ModelAdapter(OrgAccount).load_config("org_accounts", host).models
    ):
        org_account_id = organization.account_id
        role_to_assume = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
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
            org_account_id, host, role_to_assume=role_to_assume, region=config.region
        )
        all_org_structure.update(org_structure)
    redis_key = config.get_host_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        host,
        f"{host}_AWS_ORG_STRUCTURE",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get_host_specific_key(
        "celery.active_region", host, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_host_specific_key(
            "cache_organization_structure.s3.bucket", host
        )
        s3_key = config.get_host_specific_key(
            "cache_organization_structure.s3.file",
            host,
            "scps/cache_org_structure_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        all_org_structure,
        redis_key=redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        host=host,
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
    host: str,
) -> Set[str]:
    """Return a set of Organizational Unit IDs for a given account or OU ID

    Args:
        identifier: AWS account or OU ID
    """
    all_orgs = await get_org_structure(host)
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
    identifier: str, host: str
) -> ServiceControlPolicyArrayModel:
    """Retrieve a list of Service Control Policies for the account or OU specified by the identifier

    Args:
        identifier: AWS account or OU ID
    """
    all_scps = await get_all_scps(host)
    account_ous = await get_organizational_units_for_account(identifier, host)
    scps_for_account = []
    for org_account_id, scps in all_scps.items():
        # Iterate through each org's SCPs and see if the provided account_id is in the targets
        for scp in scps:
            if await _scp_targets_account_or_ou(scp, identifier, account_ous):
                scps_for_account.append(scp)
    scps = ServiceControlPolicyArrayModel(__root__=scps_for_account)
    return scps


async def minimize_iam_policy_statements(
    inline_iam_policy_statements: List[Dict], disregard_sid=True
) -> List[Dict]:
    """
    Minimizes a list of inline IAM policy statements.

    1. Policies that are identical except for the resources will have the resources merged into a single statement
    with the same actions, effects, conditions, etc.

    2. Policies that have an identical resource, but different actions, will be combined if the rest of the policy
    is identical.
    :param inline_iam_policy_statements: A list of IAM policy statement dictionaries
    :return: A potentially more compact list of IAM policy statement dictionaries
    """
    exclude_ids = []
    minimized_statements = []

    inline_iam_policy_statements = await normalize_policies(
        inline_iam_policy_statements
    )

    for i in range(len(inline_iam_policy_statements)):
        inline_iam_policy_statement = inline_iam_policy_statements[i]
        if disregard_sid:
            inline_iam_policy_statement.pop("Sid", None)
        if i in exclude_ids:
            # We've already combined this policy with another. Ignore it.
            continue
        for j in range(i + 1, len(inline_iam_policy_statements)):
            if j in exclude_ids:
                # We've already combined this policy with another. Ignore it.
                continue
            inline_iam_policy_statement_to_compare = inline_iam_policy_statements[j]
            if disregard_sid:
                inline_iam_policy_statement_to_compare.pop("Sid", None)
            # Check to see if policy statements are identical except for a given element. Merge the policies
            # if possible.
            for element in [
                "Resource",
                "Action",
                "NotAction",
                "NotResource",
                "NotPrincipal",
            ]:
                if not (
                    inline_iam_policy_statement.get(element)
                    or inline_iam_policy_statement_to_compare.get(element)
                ):
                    # This function won't handle `Condition`.
                    continue
                diff = DeepDiff(
                    inline_iam_policy_statement,
                    inline_iam_policy_statement_to_compare,
                    ignore_order=True,
                    exclude_paths=[f"root['{element}']"],
                )
                if not diff:
                    exclude_ids.append(j)
                    # Policy can be minimized
                    inline_iam_policy_statement[element] = sorted(
                        list(
                            set(
                                inline_iam_policy_statement[element]
                                + inline_iam_policy_statement_to_compare[element]
                            )
                        )
                    )
                    break

    for i in range(len(inline_iam_policy_statements)):
        if i not in exclude_ids:
            inline_iam_policy_statements[i] = sort_dict(inline_iam_policy_statements[i])
            minimized_statements.append(inline_iam_policy_statements[i])
    # TODO(cccastrapel): Intelligently combine actions and/or resources if they include wildcards
    minimized_statements = await normalize_policies(minimized_statements)
    return minimized_statements


async def normalize_policies(policies: List[Any]) -> List[Any]:
    """
    Normalizes policy statements to ensure appropriate AWS policy elements are lists (such as actions and resources),
    lowercase, and sorted. It will remove duplicate entries and entries that are superseded by other elements.
    """

    for policy in policies:
        for element in [
            "Resource",
            "Action",
            "NotAction",
            "NotResource",
            "NotPrincipal",
        ]:
            if not policy.get(element):
                continue
            if isinstance(policy.get(element), str):
                policy[element] = [policy[element]]
            # Policy elements can be lowercased, except for resources. Some resources
            # (such as IAM roles) are case sensitive
            if element in ["Resource", "NotResource", "NotPrincipal"]:
                policy[element] = list(set(policy[element]))
            else:
                policy[element] = list(set([x.lower() for x in policy[element]]))
            modified_elements = set()
            for i in range(len(policy[element])):
                matched = False
                # Sorry for the magic. this is iterating through all elements of a list that aren't the current element
                for compare_value in policy[element][:i] + policy[element][(i + 1) :]:
                    if compare_value == policy[element][i]:
                        matched = True
                        break
                    if compare_value == "*":
                        matched = True
                        break
                    if (
                        "*" not in compare_value
                        and ":" in policy[element][i]
                        and ":" in compare_value
                    ):
                        if (
                            compare_value.split(":")[0]
                            != policy[element][i].split(":")[0]
                        ):
                            continue
                    if fnmatch.fnmatch(policy[element][i], compare_value):
                        matched = True
                        break
                if not matched:
                    modified_elements.add(policy[element][i])
            policy[element] = sorted(modified_elements)
    return policies


def allowed_to_sync_role(
    role_arn: str,
    role_tags: List[Optional[Dict[str, str]]],
    host: str,
) -> bool:
    """
    This function determines whether ConsoleMe is allowed to sync or otherwise manipulate an IAM role. By default,
    ConsoleMe will sync all roles that it can get its grubby little hands on. However, ConsoleMe administrators can tell
    ConsoleMe to only sync roles with either 1) Specific ARNs, or 2) Specific tag key/value pairs. All configured tags
    must exist on the role for ConsoleMe to sync it.

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

    :return: boolean specifying whether ConsoleMe is allowed to sync / access the role
    """
    allowed_tags = config.get_host_specific_key("roles.allowed_tags", host, {})
    allowed_arns = config.get_host_specific_key("roles.allowed_arns", host, [])
    if not allowed_tags and not allowed_arns:
        return True

    if role_arn in allowed_arns:
        return True

    # Convert list of role tag dicts to a single key/value dict of tags
    # ex:
    # role_tags = [{'Key': 'consoleme-authorized', 'Value': 'consoleme_admins'},
    # {'Key': 'Description', 'Value': 'ConsoleMe OSS Demo Role'}]
    # so: actual_tags = {'consoleme-authorized': 'consoleme_admins', 'Description': 'ConsoleMe OSS Demo Role'}
    actual_tags = {
        d["Key"]: d["Value"] for d in role_tags
    }  # Convert List[Dicts] to 1 Dict

    # All configured allowed_tags must exist in the role's actual_tags for this condition to pass
    if allowed_tags and allowed_tags.items() <= actual_tags.items():
        return True
    return False


async def remove_expired_request_changes(
    extended_request: ExtendedRequestModel,
    host: str,
    user: str,
    force_refresh: bool = False,
) -> None:
    """
    If this feature is enabled, it will look at changes and remove those that are expired policies if they have been.
    Changes can be designated as temporary by defining an expiration date.
    In the future, we may allow specifying temporary policies by `Sid` or other means.
    """
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
            "managed_resource",
            "resource_policy",
            "sts_resource_policy",
        ]:
            principal_arn = change.arn

        arn_parsed = parse_arn(principal_arn)
        # resource name is none for s3 buckets
        principal_name = (arn_parsed["resource_path"] or "").split("/")[-1]

        resource_type = arn_parsed["service"]
        resource_name = arn_parsed["resource"]
        resource_region = arn_parsed["region"]
        resource_account = arn_parsed["account"]

        if not resource_account:
            resource_account = await get_resource_account(principal_arn, host)

        if resource_type == "s3" and not resource_region:
            resource_region = await get_bucket_location_with_fallback(
                resource_name, resource_account, host
            )

        if not resource_account:
            # If we don't have resource_account (due to resource not being in Config or 3rd Party account),
            # we can't revoke this change
            log_data["message"] = "Resource account not found"
            log.warning(log_data)
            continue

        client = await aio_wrapper(
            boto3_cached_conn,
            resource_type,
            host,
            user,
            service_type="client",
            future_expiration_minutes=15,
            account_number=resource_account,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
            .with_query({"account_id": resource_account})
            .first.name,
            region=resource_region or config.region,
            session_name=sanitize_session_name("revoke-expired-policies"),
            arn_partition="aws",
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            retry_max_attempts=2,
        )

        if change.change_type == "inline_policy":
            try:
                if resource_name == "role":
                    await aio_wrapper(
                        client.delete_role_policy,
                        RoleName=principal_name,
                        PolicyName=change.policy_name,
                    )
                elif resource_name == "user":
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
                ] = f"{change.policy_name} was not attached to {resource_name}"
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
                if resource_name == "role":
                    await aio_wrapper(
                        client.delete_role_permissions_boundary,
                        RoleName=principal_name,
                    )
                elif resource_name == "user":
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
                ] = f"permission boundary was not attached to {resource_name}"
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
                if resource_name == "role":
                    await aio_wrapper(
                        client.detach_role_policy,
                        RoleName=principal_name,
                        PolicyArn=change.arn,
                    )
                elif resource_name == "user":
                    await aio_wrapper(
                        client.detach_user_policy,
                        UserName=principal_name,
                        PolicyArn=change.arn,
                    )
                change.status = Status.expired
                should_update_policy_request = True

            except client.exceptions.NoSuchEntityException:
                log_data["message"] = "Policy was not found"
                log_data["error"] = f"{change.arn} was not attached to {resource_name}"
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
                    client, resource_name, principal_name, change.key, change.value
                )
                change.status = Status.expired
                should_update_policy_request = True
                force_refresh = True

            except client.exceptions.NoSuchEntityException:
                log_data["message"] = "Policy was not found"
                log_data["error"] = f"{change.key} was not attached to {resource_name}"
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
                    get_active_tear_users_tag(host),
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
                        resource_type,
                        resource_name,
                        resource_region,
                        host,
                        user,
                    )

                elif change.change_type == "sts_resource_policy":
                    role = await get_role_details(
                        resource_account,
                        principal_name,
                        host,
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

                if resource_type == "s3":
                    if len(new_policy_statement) == 0:
                        await aio_wrapper(
                            client.delete_bucket_policy,
                            Bucket=resource_name,
                            ExpectedBucketOwner=resource_account,
                        )
                    else:
                        await aio_wrapper(
                            client.put_bucket_policy,
                            Bucket=resource_name,
                            Policy=ujson.dumps(
                                existing_policy, escape_forward_slashes=False
                            ),
                        )
                elif resource_type == "sns":
                    await aio_wrapper(
                        client.set_topic_attributes,
                        TopicArn=change.arn,
                        AttributeName="Policy",
                        AttributeValue=ujson.dumps(
                            existing_policy, escape_forward_slashes=False
                        ),
                    )
                elif resource_type == "sqs":
                    queue_url: dict = await aio_wrapper(
                        client.get_queue_url, QueueName=resource_name
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
                            Attributes={
                                "Policy": ujson.dumps(
                                    existing_policy,
                                    escape_forward_slashes=False,
                                )
                            },
                        )
                elif resource_type == "iam":
                    await aio_wrapper(
                        client.update_assume_role_policy,
                        RoleName=principal_name,
                        PolicyDocument=ujson.dumps(
                            existing_policy, escape_forward_slashes=False
                        ),
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
            await IAMRequest.write_v2(extended_request, host)

            if resource_name == "role":
                await IAMRole.get(
                    resource_account,
                    principal_arn,
                    host,
                    force_refresh=force_refresh,
                    run_sync=True,
                )

            elif resource_name == "user":
                await fetch_iam_user(
                    resource_account,
                    principal_arn,
                    host,
                    force_refresh=force_refresh,
                    run_sync=True,
                )

        except Exception as e:
            log_data["message"] = "Exception unable to update policy status to expired"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()


async def remove_expired_host_requests(host: str):
    all_requests = await aio_wrapper(
        IAMRequest.query, host, filter_condition=(IAMRequest.status == "approved")
    )

    for request in all_requests:
        await remove_expired_request_changes(
            ExtendedRequestModel.parse_obj(request.extended_request.dict()), host, None
        )

    # Can swap back to this once it's thread safe
    # await asyncio.gather(*[
    #     remove_expired_request_changes(ExtendedRequestModel.parse_obj(request["extended_request"]), host, None)
    #     for request in all_policy_requests
    # ])


async def remove_all_expired_requests() -> dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    hosts = get_all_hosts()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_hosts": len(hosts),
    }
    log.debug(log_data)
    await asyncio.gather(*[remove_expired_host_requests(host) for host in hosts])

    return log_data


def get_aws_principal_owner(role_details: Dict[str, Any], host: str) -> Optional[str]:
    """
    Identifies the owning user/group of an AWS principal based on one or more trusted and configurable principal tags.
    `owner` is used to notify application owners of permission problems with their detected AWS principals or resources
    if another identifier (ie: session name) for a principal doesn't point to a specific user for notification.

    :return: owner: str
    """
    owner = None
    owner_tag_names = config.get_host_specific_key("aws.tags.owner", host, [])
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


async def resource_arn_known_in_aws_config(
    resource_arn: str,
    host: str,
    run_query: bool = True,
    run_query_with_aggregator: bool = True,
) -> bool:
    """
    Determines if the resource ARN is known in AWS Config. AWS config does not store all resource
    types, nor will it account for cross-organizational resources, so the result of this function shouldn't be used
    to determine if a resource "exists" or not.

    A more robust approach is determining the resource type and querying AWS API directly to see if it exists, but this
    requires a lot of code.

    Note: This data may be stale by ~ 1 hour and 15 minutes (local results caching + typical AWS config delay)

    :param resource_arn: ARN of the resource we want to look up
    :param run_query: Should we run an AWS config query if we're not able to find the resource in our AWS Config cache?
    :param run_query_with_aggregator: Should we run the AWS Config query on our AWS Config aggregator?
    :return:
    """
    red = RedisHandler().redis_sync(host)
    expiration_seconds: int = config.get_host_specific_key(
        "aws.resource_arn_known_in_aws_config.expiration_seconds",
        host,
        3600,
    )
    known_arn = False
    if not resource_arn.startswith("arn:aws:"):
        return known_arn

    resources_from_aws_config_redis_key: str = config.get_host_specific_key(
        "aws_config_cache.redis_key",
        host,
        f"{host}_AWSCONFIG_RESOURCE_CACHE",
    )

    if red.exists(resources_from_aws_config_redis_key) and red.hget(
        resources_from_aws_config_redis_key, resource_arn
    ):
        return True

    resource_arn_exists_temp_matches_redis_key: str = config.get_host_specific_key(
        "resource_arn_known_in_aws_config.redis.temp_matches_key",
        host,
        f"{host}_TEMP_QUERIED_RESOURCE_ARN_CACHE",
    )

    # To prevent repetitive queries against AWS config, first see if we've already ran a query recently
    result = await redis_hgetex(
        resource_arn_exists_temp_matches_redis_key, resource_arn, host
    )
    if result:
        return result["known"]

    if not run_query:
        return False

    r = await aio_wrapper(
        query,
        f"select arn where arn = '{resource_arn}'",
        host,
        use_aggregator=run_query_with_aggregator,
    )
    if r:
        known_arn = True
    # To prevent future repetitive queries on AWS Config, set our result in Redis with an expiration
    await redis_hsetex(
        resource_arn_exists_temp_matches_redis_key,
        resource_arn,
        {"known": known_arn},
        expiration_seconds,
        host,
    )

    return known_arn


async def simulate_iam_principal_action(
    principal_arn,
    action,
    resource_arn,
    source_ip,
    host,
    user,
    expiration_seconds: Optional[int] = None,
):
    """
    Simulates an IAM principal action affecting a resource

    :return:
    """
    if not expiration_seconds:
        expiration_seconds = (
            config.get_host_specific_key(
                "aws.simulate_iam_principal_action.expiration_seconds",
                host,
                3600,
            ),
        )
    # simulating IAM principal policies is expensive.
    # Temporarily cache and return results by principal_arn, action, and resource_arn. We don't consider source_ip
    # when caching because it could vary greatly for application roles running on multiple instances/containers.
    resource_arn_exists_temp_matches_redis_key: str = config.get_host_specific_key(
        "resource_arn_known_in_aws_config.redis.temp_matches_key",
        host,
        f"{host}_TEMP_POLICY_SIMULATION_CACHE",
    )

    cache_key = f"{principal_arn}-{action}-{resource_arn}"
    result = await redis_hgetex(
        resource_arn_exists_temp_matches_redis_key, cache_key, host
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
        host,
        user,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        retry_max_attempts=2,
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
            host,
        )
    except Exception:
        sentry_sdk.capture_exception()
        return None
    return response["EvaluationResults"]


async def get_iam_principal_owner(arn: str, aws: Any, host: str) -> Optional[str]:
    principal_details = {}
    principal_type = await get_identity_type_from_arn(arn)
    account_id = await get_account_id_from_arn(arn)
    # trying to find principal for subsequent queries
    if principal_type == "role":
        principal_details = (await IAMRole.get(account_id, arn, host)).dict()
    elif principal_type == "user":
        principal_details = await fetch_iam_user(account_id, arn, host)
    return principal_details.get("owner")


async def get_resource_account(arn: str, host: str) -> str:
    """Return the AWS account ID that owns a resource.

    In most cases, this will pull the ID directly from the ARN.
    If we are unsuccessful in pulling the account from ARN, we try to grab it from our resources cache
    """
    red = await RedisHandler().redis(host)
    resource_account: str = get_account_from_arn(arn)
    if resource_account:
        return resource_account

    resources_from_aws_config_redis_key: str = config.get_host_specific_key(
        "aws_config_cache.redis_key",
        host,
        f"{host}_AWSCONFIG_RESOURCE_CACHE",
    )

    if not red.exists(resources_from_aws_config_redis_key):
        # This will force a refresh of our redis cache if the data exists in S3
        await retrieve_json_data_from_redis_or_s3(
            redis_key=resources_from_aws_config_redis_key,
            s3_bucket=config.get_host_specific_key(
                "aws_config_cache_combined.s3.bucket", host
            ),
            s3_key=config.get_host_specific_key(
                "aws_config_cache_combined.s3.file",
                host,
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            ),
            redis_data_type="hash",
            host=host,
            default={},
        )

    resource_info = await redis_hget(resources_from_aws_config_redis_key, arn, host)
    if resource_info:
        return json.loads(resource_info).get("accountId", "")
    elif "arn:aws:s3:::" in arn:
        # Try to retrieve S3 bucket information from S3 cache. This is inefficient and we should ideally have
        # retrieved this info from our AWS Config cache, but we've encountered problems with AWS Config historically
        # that have necessitated this code.
        s3_cache = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get_host_specific_key(
                "redis.s3_buckets_key", host, f"{host}_S3_BUCKETS"
            ),
            redis_data_type="hash",
            host=host,
        )
        search_bucket_name = arn.split(":")[-1]
        for bucket_account_id, buckets in s3_cache.items():
            buckets_j = json.loads(buckets)
            if search_bucket_name in buckets_j:
                return bucket_account_id
    return ""


async def should_exclude_policy_from_comparison(policy: Dict[str, Any]) -> bool:
    """Ignores policies from comparison if we don't support them.

    AWS IAM policies come in all shapes and sizes. We ignore policies that have Effect=Deny, or NotEffect (instead of Effect),
    NotResource (instead of Resource), and NotAction (instead of Action).

    :param policy: A policy dictionary, ie: {'Statement': [{'Action': 's3:*', 'Effect': 'Allow', 'Resource': '*'}]}
    :return: Whether to exclude the policy from comparison or not.
    """
    if not policy.get("Effect") or policy["Effect"] == "Deny":
        return True
    if not policy.get("Resource"):
        return True
    if not policy.get("Action"):
        return True
    return False


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


async def combine_all_policy_statements(
    policies: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Takes a list of policies and combines them into a single list of policies. This is useful for combining inline
    policies and managed policies into a single list of policies.

    :param policies: A List of policies. IE: [{'Action': ['s3:*'], 'Effect': 'Allow', 'Resource': ['*']}, ...]
    :return: a combined list of policies.
    """
    combined_policies = []
    for policy in policies:
        if isinstance(policy.get("Statement"), list):
            for statement in policy["Statement"]:
                combined_policies.append(statement)
        else:
            combined_policies.append(policy)
    return combined_policies


async def calculate_policy_changes(
    identity: Dict[str, Any],
    used_services: Set[str],
    policy_type: str,
    managed_policy_details: Dict[str, Any] = None,
):
    """Given the identity, the list of used_services (not permissions, but services like `s3`, `sqs`, etc), the policy type
    (inline_policy or manage_policy), and the managed policy details (if applicable), this function will calculate the
    changes that need to be made to the identity's policies to remove all unused services.

    :param identity: Details about the AWS IAM Role or User.
    :param used_services: A set or list of used services.
    :param policy_type: Either inline_policy or manage_policy.
    :param managed_policy_details: A dictionary of managed policy name to the default managed policy document, defaults to None.
    :raises Exception: Raises an exception on validation error.
    :return: Returns effective policy as-is, effective policy with unused services removed, and individual changes to a role's
        list of internal policies.
    """
    if policy_type == "inline_policy":
        identity_policy_list_name = "RolePolicyList"
    elif policy_type == "managed_policy":
        identity_policy_list_name = "AttachedManagedPolicies"
    else:
        raise Exception("Invalid policy type")
    all_before_policy_statements = []
    all_after_policy_statements = []
    individual_role_policy_changes = []
    for policy in identity["policy"].get(identity_policy_list_name, []):
        if policy_type == "managed_policy":
            before_policy_document = managed_policy_details[policy["PolicyName"]]
        else:
            before_policy_document = policy["PolicyDocument"]
        computed_changes = {
            "policy_type": policy_type,
            "policy_name": policy["PolicyName"],
            "before_policy_document": before_policy_document,
        }
        if policy_type == "managed_policy":
            computed_changes["policy_arn"] = policy["PolicyArn"]
        after_policy_statements = []
        before_policy_document_copy = copy.deepcopy(before_policy_document)
        for statement in before_policy_document_copy["Statement"]:
            all_before_policy_statements.append(copy.deepcopy(statement))
            new_actions = set()
            new_resources = set()
            if await should_exclude_policy_from_comparison(statement):
                after_policy_statements.append(statement)
                continue
            if isinstance(statement["Action"], str):
                statement["Action"] = [statement["Action"]]
            for action in statement["Action"]:
                if used_services and action == "*":
                    for service in used_services:
                        new_actions.add(f"{service}:*")
                elif action.split(":")[0] in used_services:
                    new_actions.add(action)
            if isinstance(statement["Resource"], str):
                statement["Resource"] = [statement["Resource"]]

            for resource in statement["Resource"]:
                if resource == "*":
                    new_resources.add(resource)
                elif resource.split(":")[2] in used_services:
                    new_resources.add(resource)
            if new_actions and new_resources:
                statement["Action"] = list(new_actions)
                statement["Resource"] = list(new_resources)
                after_policy_statements.append(statement)
                all_after_policy_statements.append(statement)
                continue
        if after_policy_statements:
            computed_changes["after_policy_document"] = {
                "Statement": after_policy_statements,
            }
            if before_policy_document.get("Version"):
                computed_changes["after_policy_document"][
                    "Version"
                ] = before_policy_document["Version"]
            individual_role_policy_changes.append(computed_changes)
    return {
        "all_before_policy_statements": all_before_policy_statements,
        "all_after_policy_statements": all_after_policy_statements,
        "individual_role_policy_changes": individual_role_policy_changes,
    }


def get_regex_resource_names(statement: dict) -> list:
    """Generates a list of resource names for a statement that can be used for regex searches

    :param statement: A statement, IE: {
        'Action': ['s3:listbucket', 's3:list*'],
        'Effect': 'Allow',
        'Resource': ["arn:aws:dynamodb:*:*:table/TableOne", "arn:aws:dynamodb:*:*:table/TableTwo"]
    }
    :return: A list of resource names to be used for regex checks, IE: [
        "Allow:arn:aws:dynamodb:.*:.*:table/Table", "Allow:arn:aws:dynamodb:.*:.*:table/Table"
    ]
    """
    return [
        f"{statement.get('Effect')}:{resource}".replace("*", ".*")
        for resource in statement.get("Resource")
    ]


async def is_resource_match(regex_patterns, regex_strs) -> bool:
    """Check if all provided strings (regex_strs) match on AT LEAST ONE regex pattern

    :param regex_patterns: A list of regex patterns to search on
    :param regex_strs: A list of strings to check against
    """

    async def _regex_check(regex_pattern) -> bool:
        return any(re.match(regex_pattern, regex_str) for regex_str in regex_strs)

    results = await asyncio.gather(
        *[_regex_check(regex_pattern) for regex_pattern in regex_patterns]
    )
    return all(r for r in results)


async def reduce_statement_actions(statement: dict) -> dict:
    """Removes redundant actions from a statement and stores a regex map of the reduced.

    :param statement: A normalized statement, IE: {
        'Action': ['s3:listbucket', 's3:list*'], 'Effect': 'Allow', 'Resource': ['*']
    }
    :return: A statement with all redundant actions removed, IE: {
        'Action': ['s3:list*'], 'Effect': 'Allow', 'Resource': ['*']
    }
    """
    actions = statement.get("Action", [])

    if not isinstance(actions, list):
        actions = [actions]
    else:
        actions = sorted(set(actions))

    if "*" in actions:
        # Not sure if we should really be allowing this but
        #   if they've added a wildcard action there isn't any need to check what hits
        statement["Action"] = ["*"]
        return statement

    # Create a map of actions grouped by resource to prevent unnecessary checks
    resource_regex_map = defaultdict(list)
    for action in actions:
        # Represent the action as the regex lookup so this isn't being done on every iteration
        if "*" in action:
            resource_regex_map[action.split(":")[0]].append(action.replace("*", ".*"))

    async def _regex_check(action_str) -> str:
        # Check if the provided string hits on any other action for the same resource type
        # If not, return the string to be used as part of the reduced set of actions
        action_str_re = action_str.replace("*", ".*")
        action_resource = action_str.split(":")[0]

        resource_actions = resource_regex_map[action_resource]
        if not any(
            re.match(related_action, action_str_re, re.IGNORECASE)
            for related_action in resource_actions
            if related_action != action_str_re
        ):
            return action_str

    reduced_actions = await asyncio.gather(
        *[_regex_check(action_str) for action_str in actions]
    )
    statement["Action"] = [action.lower() for action in reduced_actions if action]

    return statement


async def normalize_statement(statement: dict) -> dict:
    """Refactors the statement dict and adds additional keys to be used for easy regex checks.

    :param statement: A statement, IE: {
        'Action': ['s3:listbucket', 's3:list*'], 'Effect': 'Allow', 'Resource': '*'
    }
    :return: A statement with all redundant actions removed, IE: {
        'Action': ['s3:listbucket', 's3:list*'],
        'ActionMap': {'s3': ['listbucket', 's3:list.*']},
        'Effect': 'Allow',
        'Resource': ['*']
        'ResourceAsRegex': ['.*']
    }
    """
    statement.pop("Sid", None)  # Drop the statement ID

    # Ensure Resource is a sorted list
    if not isinstance(statement["Resource"], list):
        statement["Resource"] = [statement["Resource"]]

    if "*" in statement["Resource"] and len(statement["Resource"]) > 1:
        statement["Resource"] = ["*"]
    else:
        statement["Resource"].sort()

    # Add the regex repr of the resource to be used when comparing statements in a policy
    statement["ResourceAsRegex"] = [
        f"{statement.get('Effect')}:{resource}".replace("*", ".*")
        for resource in statement.get("Resource")
    ]

    statement = await reduce_statement_actions(statement)

    # Create a map of actions grouped by resource to prevent unnecessary checks
    statement["ActionMap"] = defaultdict(set)
    for action in statement["Action"]:
        # Represent the action as the regex lookup so this isn't being done on every iteration
        # if "*" in action:
        statement["ActionMap"][action.split(":")[0]].add(action.replace("*", ".*"))

    return statement


async def condense_statements(
    statements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Removes redundant policies, and actions that are already permitted by a different wildcard / partial wildcard
    statement.

    :param statements: A list of statements, IE: [
        {'Action': ['s3:listbucket'], 'Effect': 'Allow', 'Resource': ['*']},
        {'Action': ['s3:listbucket'], 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::bucket']},
        ...
    ]
    :return: A list of statements with all redundant policies removed, IE: [
        {'Action': ['s3:listbucket'], 'Effect': 'Allow', 'Resource': ['*']},
        ...
    ]
    """
    statements = await asyncio.gather(
        *[normalize_statement(statement) for statement in statements]
    )

    # statements.copy() so we don't mess up enumeration when popping statements with identical resource+effect
    # The offset variables are so we can access the correct element after elements have been removed
    pop_offset = 0
    for elem, statement in enumerate(statements.copy()):
        offset_elem = elem - pop_offset

        if statement["Action"][0] == "*" or statement.get("Condition"):
            # Don't mess with statements that allow everything or have a condition
            continue

        for inner_elem, inner_statement in enumerate(statements):
            if offset_elem == inner_elem:
                continue
            elif not await is_resource_match(
                inner_statement["ResourceAsRegex"], statement["ResourceAsRegex"]
            ):
                continue
            elif inner_statement.get("Condition"):
                continue
            elif (
                len(inner_statement["Action"]) == 1
                and inner_statement["Action"][0] == "*"
            ):
                continue
            elif (
                statement["Effect"] == inner_statement["Effect"]
                and statement["Resource"] == inner_statement["Resource"]
            ):
                # The statements are identical so combine the actions
                statements[inner_elem]["Action"] = sorted(
                    list(set(statements[inner_elem]["Action"] + statement["Action"]))
                )
                for resource_type, perm_set in statement["ActionMap"].items():
                    for perm in perm_set:
                        statements[inner_elem]["ActionMap"][resource_type].add(perm)

                del statements[offset_elem]
                pop_offset += 1
                break

            action_pop_offset = 0
            # statement["Action"].copy() so we don't mess up enumerating Action when popping elements
            for action_elem, action in enumerate(statement["Action"].copy()):
                offset_action_elem = action_elem - action_pop_offset
                action_re = action.replace("*", ".*")
                action_resource = action.split(":")[0]
                resource_actions = inner_statement["ActionMap"][action_resource]

                if any(
                    re.match(related_action, action_re, re.IGNORECASE)
                    for related_action in resource_actions
                ):
                    # If the action falls under a different (inner) statement, remove it.
                    del statements[offset_elem]["Action"][offset_action_elem]
                    action_pop_offset += 1
                    statements[offset_elem]["ActionMap"][action_resource] = set(
                        act_re
                        for act_re in statements[offset_elem]["ActionMap"][
                            action_resource
                        ]
                        if act_re != action_re
                    )

    # Remove statements with no remaining actions and reduce actions once again to account for combined statements
    statements = await asyncio.gather(
        *[
            reduce_statement_actions(statement)
            for statement in statements
            if len(statement["Action"]) > 0
        ]
    )
    for elem in range(len(statements)):  # Remove eval keys
        statements[elem].pop("ActionMap")
        statements[elem].pop("ResourceAsRegex")

    return statements


async def get_identity_type_from_arn(arn: str) -> str:
    """Returns identity type (`user` or `role`) from an ARN.

    :param arn: Amazon Resource Name of an IAM user or role,
        ex: arn:aws:iam::123456789012:role/role_name -> returns 'role'
            arn:aws:iam::123456789012:user/user_name -> returns 'user'
    :return: Identity type (`user` or `role`)
    """
    return arn.split(":")[-1].split("/")[0]


async def get_identity_name_from_arn(arn: str) -> str:
    """Returns identity name from an ARN.

    :param arn: Amazon Resource Name of an IAM user or role,
        ex: arn:aws:iam::123456789012:role/role_name -> returns 'role_name'
            arn:aws:iam::123456789012:user/user_name -> returns 'user_name'
    :return: Identity name
    """
    return arn.split("/")[-1]


async def get_account_id_from_arn(arn: str) -> str:
    """Returns account ID from an ARN.

    :param arn: Amazon Resource Name of an IAM user or role,
        ex: arn:aws:iam::123456789012:role/role_name -> returns '123456789012'
            arn:aws:iam::123456789012:user/user_name -> returns '123456789012'
    :return: Identity name
    """
    return arn.split(":")[4]
