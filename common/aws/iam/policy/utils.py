import copy
import datetime
import fnmatch
import sys
import time
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple

import sentry_sdk
from botocore.exceptions import ClientError, ParamValidationError
from deepdiff import DeepDiff
from jinja2 import Environment, FileSystemLoader, select_autoescape
from joblib import Parallel, delayed
from parliament import analyze_policy_string, enhance_finding

from common.aws.iam.role.models import IAMRole
from common.aws.iam.role.utils import get_role_managed_policy_documents
from common.aws.iam.statement.utils import condense_statements
from common.aws.iam.user.utils import fetch_iam_user
from common.aws.utils import ResourceSummary, get_resource_account
from common.config import config
from common.config.models import ModelAdapter
from common.lib import noq_json as json
from common.lib.assume_role import ConsoleMeCloudAux, rate_limited, sts_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.access_advisor import get_epoch_authenticated
from common.lib.aws.aws_paginate import aws_paginated
from common.lib.aws.session import get_session_for_tenant
from common.lib.aws.utils import fetch_resource_details
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.generic import sort_dict
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler
from common.lib.s3_helpers import is_object_older_than_seconds
from common.models import SpokeAccount

log = config.get_logger(__name__)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()

PERMISSIONS_SEPARATOR = "||"
ALL_IAM_MANAGED_POLICIES = defaultdict(dict)


async def get_resource_policy(
    account: str, resource_type: str, name: str, region: str, tenant: str, user: str
):
    try:
        details = await fetch_resource_details(
            account, resource_type, name, region, tenant, user
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
    tenant: str,
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
                tenant,
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


@aws_paginated("AttachedPolicies")
def _get_user_managed_policies(user, client=None, **kwargs):
    return client.list_attached_user_policies(UserName=user["UserName"], **kwargs)


@sts_conn("iam", service_type="client")
@rate_limited()
def get_user_managed_policies(user, client=None, **kwargs):
    policies = _get_user_managed_policies(user, client=client, **kwargs)
    return [{"name": p["PolicyName"], "arn": p["PolicyArn"]} for p in policies]


@sts_conn("iam", service_type="client")
@rate_limited()
def get_user_managed_policy_documents(user, client=None, **kwargs):
    """Retrieve the currently active policy version document for every managed policy that is attached to the user."""
    policies = get_user_managed_policies(user, force_client=client)

    policy_names = (policy["name"] for policy in policies)
    delayed_gmpd_calls = (
        delayed(get_managed_policy_document)(policy["arn"], force_client=client)
        for policy in policies
    )
    policy_documents = Parallel(n_jobs=20, backend="threading")(delayed_gmpd_calls)

    return dict(zip(policy_names, policy_documents))


@sts_conn("iam", service_type="client")
@rate_limited()
def get_managed_policy_document(
    policy_arn, policy_metadata=None, client=None, **kwargs
):
    """Retrieve the currently active (i.e. 'default') policy version document for a policy.

    :param policy_arn:
    :param policy_metadata: This is a previously fetch managed policy response from boto/cloudaux.
                            This is used to prevent unnecessary API calls to get the initial policy default version id.
    :param client:
    :param kwargs:
    :return:
    """
    if not policy_metadata:
        policy_metadata = client.get_policy(PolicyArn=policy_arn)

    policy_document = client.get_policy_version(
        PolicyArn=policy_arn, VersionId=policy_metadata["Policy"]["DefaultVersionId"]
    )
    return policy_document["PolicyVersion"]["Document"]


@sts_conn("iam", service_type="client")
@aws_paginated("Policies")
@rate_limited()
def get_all_managed_policies(client=None, **kwargs):
    return client.list_policies(**kwargs)


@sts_conn("iam", service_type="client")
@rate_limited()
def get_policy(policy_arn, client=None, **kwargs):
    """Retrieve the IAM Managed Policy."""
    return client.get_policy(PolicyArn=policy_arn, **kwargs)


@rate_limited()
def create_managed_policy(cloudaux, name, path, policy, description, tenant):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "cloudaux": cloudaux,
        "name": name,
        "path": path,
        "policy": policy,
        "description": "description",
        "message": "Creating Managed Policy",
        "tenant": tenant,
    }
    log.debug(log_data)

    cloudaux.call(
        "iam.client.create_policy",
        PolicyName=name,
        Path=path,
        PolicyDocument=json.dumps(policy, indent=2),
        Description=description,
    )


@sts_conn("iam", service_type="client")
@rate_limited()
def get_user_inline_policy_document(user, policy_name, client=None, **kwargs):
    response = client.get_user_policy(UserName=user["UserName"], PolicyName=policy_name)
    return response.get("PolicyDocument")


@rate_limited()
@sts_conn("iam", service_type="client")
def get_user_inline_policy_names(user, client=None, **kwargs):
    marker = {}
    inline_policies = []

    while True:
        response = client.list_user_policies(UserName=user["UserName"], **marker)
        inline_policies.extend(response["PolicyNames"])

        if response["IsTruncated"]:
            marker["Marker"] = response["Marker"]
        else:
            return inline_policies


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


async def fetch_managed_policy_details(
    account_id: str, resource_name: str, tenant: str, user: str, path: str = None
) -> Optional[Dict]:
    from common.lib.policies import get_aws_config_history_url_for_resource

    if not tenant:
        raise Exception("tenant not configured")
    if path:
        resource_name = path + "/" + resource_name
    policy_arn: str = f"arn:aws:iam::{account_id}:policy/{resource_name}"
    result: Dict = {}
    result["Policy"] = await aio_wrapper(
        get_managed_policy_document,
        policy_arn=policy_arn,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        tenant=tenant,
        user=user,
    )
    policy_details = await aio_wrapper(
        get_policy,
        policy_arn=policy_arn,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        tenant=tenant,
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
        tenant,
        region=config.region,
    )

    return result


async def access_analyzer_validate_policy(
    policy: str, log_data, tenant, policy_type: str = "IDENTITY_POLICY"
) -> List[Dict[str, Any]]:
    session = get_session_for_tenant(tenant)
    try:
        enhanced_findings = []
        client = await aio_wrapper(
            session.client,
            "accessanalyzer",
            region_name=config.region,
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        access_analyzer_response = await aio_wrapper(
            client.validate_policy,
            policyDocument=policy,
            policyType=policy_type,  # Noq only supports identity policy analysis currently
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


async def validate_iam_policy(policy: str, log_data: Dict, tenant: str):
    parliament_findings: List = await parliament_validate_iam_policy(policy)
    access_analyzer_findings: List = await access_analyzer_validate_policy(
        policy, log_data, tenant, policy_type="IDENTITY_POLICY"
    )
    return parliament_findings + access_analyzer_findings


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


def get_user_inline_policies(user, **kwargs):
    policy_names = get_user_inline_policy_names(user, **kwargs)

    policies = {}
    for policy_name in policy_names:
        policies[policy_name] = get_user_inline_policy_document(
            user, policy_name, **kwargs
        )

    return policies


async def update_managed_policy(cloudaux, policy_name, new_policy, policy_arn):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "new_policy": new_policy,
        "policy_name": policy_name,
        "policy_arn": policy_arn,
        "message": "Updating managed policy",
    }
    log.debug(log_data)

    current_policy_versions = []
    default_policy_index = 0
    versions = await aio_wrapper(
        cloudaux.call, "iam.client.list_policy_versions", PolicyArn=policy_arn
    )
    oldest_policy_version = -1
    oldest_timestamp = None
    for i, version in enumerate(versions.get("Versions", [])):
        if version["IsDefaultVersion"]:
            default_policy_index = i
        current_policy_versions.append(version)
        if oldest_policy_version == -1 or oldest_timestamp > version["CreateDate"]:
            oldest_policy_version = i
            oldest_timestamp = version["CreateDate"]

    if len(current_policy_versions) == 5:
        pop_position = oldest_policy_version
        # Want to make sure we don't pop the default version so arbitrarily set position to oldest + 1 mod N
        # if default is also the oldest
        if default_policy_index == oldest_policy_version:
            pop_position = (oldest_policy_version + 1) % len(current_policy_versions)
        await aio_wrapper(
            cloudaux.call,
            "iam.client.delete_policy_version",
            PolicyArn=policy_arn,
            VersionId=current_policy_versions.pop(pop_position)["VersionId"],
        )

    await aio_wrapper(
        cloudaux.call,
        "iam.client.create_policy_version",
        PolicyArn=policy_arn,
        PolicyDocument=json.dumps(new_policy, indent=2),
        SetAsDefault=True,
    )


async def create_or_update_managed_policy(
    new_policy,
    policy_name,
    policy_arn,
    description,
    tenant,
    conn_details,
    policy_path="/",
    existing_policy=None,
):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "new_policy": new_policy,
        "policy_name": policy_name,
        "policy_arn": policy_arn,
        "description": description,
        "policy_path": policy_path,
        "existing_policy": existing_policy,
        "conn_details": conn_details,
        "tenant": tenant,
    }

    ca = await aio_wrapper(ConsoleMeCloudAux, **conn_details)

    if not existing_policy:
        log_data["message"] = "Policy does not exist. Creating"
        log.debug(log_data)
        await aio_wrapper(
            create_managed_policy,
            ca,
            policy_name,
            policy_path,
            new_policy,
            description,
            tenant,
        )
        return

    log_data["message"] = "Policy exists and needs to be updated"
    log.debug(log_data)
    # Update the managed policy
    await update_managed_policy(ca, policy_name, new_policy, policy_arn)


async def get_all_iam_managed_policies_for_account(account_id, tenant):
    global ALL_IAM_MANAGED_POLICIES
    # TODO: Use redis clusters for this type of thing and not a global var
    policy_key: str = config.get_tenant_specific_key(
        "redis.iam_managed_policies_key",
        tenant,
        f"{tenant}_IAM_MANAGED_POLICIES",
    )
    current_time = time.time()
    if current_time - ALL_IAM_MANAGED_POLICIES[tenant].get("last_update", 0) > 500:
        red = await RedisHandler().redis(tenant)
        ALL_IAM_MANAGED_POLICIES[tenant]["managed_policies"] = await aio_wrapper(
            red.hgetall, policy_key
        )
        ALL_IAM_MANAGED_POLICIES[tenant]["last_update"] = current_time

    if ALL_IAM_MANAGED_POLICIES[tenant].get("managed_policies"):
        return json.loads(
            ALL_IAM_MANAGED_POLICIES[tenant]["managed_policies"].get(account_id, "[]")
        )
    else:
        s3_bucket = config.get_tenant_specific_key(
            "account_resource_cache.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "account_resource_cache.s3.file",
            tenant,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="managed_policies", account_id=account_id)
        return await retrieve_json_data_from_redis_or_s3(
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            default=[],
            tenant=tenant,
        )


async def calculate_effective_policy_for_identity(
    tenant, arn, managed_policies, force_refresh=False
):
    """
    Calculate the effective policy for a given tenant and arn
    """

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "arn": arn,
        "tenant": tenant,
    }

    resource_summary = await ResourceSummary.set(tenant, arn)
    account_id = resource_summary.account
    identity_type = resource_summary.resource_type
    if identity_type == "role":
        identity = (
            await IAMRole.get(
                tenant, account_id, arn, force_refresh=force_refresh, run_sync=True
            )
        ).dict()
        identity_policy_list_name = "RolePolicyList"
        identity_name_parameter = "RoleName"
    elif identity_type == "user":
        identity = await fetch_iam_user(account_id, arn, tenant, run_sync=True)
        identity_policy_list_name = "UserPolicyList"
        identity_name_parameter = "UserName"
    else:
        raise Exception("Unknown identity type: {}".format(identity_type))

    identity_name = identity["name"]

    spoke_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name
    )
    if not spoke_role_name:
        log.error({**log_data, "message": "No spoke role name found"})
        raise

    # TODO: This is an expensive job. We should pull managed policy details from our cache
    managed_policy_details = get_role_managed_policy_documents(
        {identity_name_parameter: identity_name},
        account_number=account_id,
        assume_role=spoke_role_name,
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        tenant=tenant,
    )
    combined_policy_statements = []
    for policy in identity["policy"].get(identity_policy_list_name, []):
        policy_statements = policy["PolicyDocument"]["Statement"]
        if isinstance(policy_statements, dict):
            policy_statements = [policy_statements]
        combined_policy_statements.extend(policy_statements)

    for policy in identity["policy"]["AttachedManagedPolicies"]:
        policy_statements = managed_policy_details[policy["PolicyName"]]["Statement"]
        if isinstance(policy_statements, dict):
            policy_statements = [policy_statements]
        combined_policy_statements.extend(policy_statements)

    condensed_combined_policy_statements = await condense_statements(
        combined_policy_statements
    )
    return condensed_combined_policy_statements


async def calculate_unused_policy_for_identity(
    tenant: str,
    account_id: str,
    identity_name: str,
    identity_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates and stories effective and unused policies for an identity.

    :param tenant: Tenant ID
    :param account_id: AWS Account ID
    :param identity_name: IAM Identity Name (Role name or User name)
    :param identity_type: "role" or "user", defaults to None
    :raises Exception: Raises an exception if there is a validation error
    :return: Returns a dictionary of effective and "repoed" policy documents.
    """

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "tenant": tenant,
    }
    if not identity_type:
        raise Exception("Unable to generate unused policy without identity type")
    arn = f"arn:aws:iam::{account_id}:{identity_type}/{identity_name}"

    s3_bucket = config.get_tenant_specific_key(
        "calculate_unused_policy_for_identity.s3.bucket",
        tenant,
        config.get(
            "_global_.s3_cache_bucket",
        ),
    )

    s3_key = config.get_tenant_specific_key(
        "calculate_unused_policy_for_identity.s3.file",
        tenant,
        f"calculate_unused_policy_for_identity/{arn}.json.gz",
    )

    if not await is_object_older_than_seconds(
        s3_key, bucket=s3_bucket, tenant=tenant, older_than_seconds=86400
    ):
        return await retrieve_json_data_from_redis_or_s3(
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )

    identity_type_string = "RoleName" if identity_type == "role" else "UserName"
    try:
        spoke_role_name = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name
        )
        if not spoke_role_name:
            log.error({**log_data, "message": "No spoke role name found"})
            raise

        managed_policy_details = await aio_wrapper(
            get_role_managed_policy_documents,
            {identity_type_string: identity_name},
            account_number=account_id,
            assume_role=spoke_role_name,
            region=config.region,
            retry_max_attempts=2,
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            tenant=tenant,
        )
    except Exception:
        sentry_sdk.capture_exception()
        raise

    effective_identity_permissions = await calculate_unused_policy_for_identities(
        tenant,
        [arn],
        managed_policy_details,
        account_id=account_id,
    )
    await store_json_results_in_redis_and_s3(
        effective_identity_permissions[arn],
        tenant=tenant,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )
    return effective_identity_permissions[arn]


async def generate_permission_removal_commands(
    tenant: str, identity: Any, new_policy_document: Dict[str, Any]
) -> Dict[str, str]:
    """Generates Python and AWS CLI commands to remove unused permissions.

    Generated commands will: 1) add new policy to identity, 2) remove all other policies from identity.

    :param tenant: tenant name
    :param identity: Dictionary of identity details
    :param new_policy_document: New policy document with all unused permissions removed
    :return: A dictionary of AWS CLI and Python commands to remove unused permissions
    """
    resource_summary = await ResourceSummary.set(tenant, identity["arn"])
    identity_type = resource_summary.resource_type
    identity_name = resource_summary.name
    inline_policy_names = [
        policy["PolicyName"] for policy in identity["policy"].get("RolePolicyList", [])
    ]
    managed_policy_arns = [
        policy["PolicyArn"]
        for policy in identity["policy"].get("AttachedManagedPolicies", [])
    ]
    new_policy_name = f"{identity_name}-policy"
    env = Environment(
        loader=FileSystemLoader("common/templates"),
        extensions=["jinja2.ext.loopcontrols"],
        autoescape=select_autoescape(),
    )
    aws_cli_template = env.get_template("aws_cli_permissions_removal.py.j2")
    aws_cli_script = aws_cli_template.render(
        identity_type=identity_type,
        identity_name=identity_name,
        new_policy_name=new_policy_name,
        managed_policy_arns=managed_policy_arns,
        inline_policy_names=inline_policy_names,
        new_policy_document=json.dumps(new_policy_document),
    )
    python_boto3_template = env.get_template("boto3_permissions_removal.py.j2")
    python_boto3_script = python_boto3_template.render(
        identity_type=identity_type,
        identity_name=identity_name,
        new_policy_name=new_policy_name,
        managed_policy_arns=managed_policy_arns,
        inline_policy_names=inline_policy_names,
        new_policy_document=json.dumps(new_policy_document, indent=2),
    )
    return {
        "aws_cli_script": aws_cli_script,
        "python_boto3_script": python_boto3_script,
    }


async def calculate_unused_policy_for_identities(
    tenant: str,
    arns: List[str],
    managed_policy_details: Dict[str, Any],
    access_advisor_data: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
    account_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Generates effective and unused policies for a list of identities.

    :param tenant: Tenant ID
    :param arns: A list of ARNs to calculate unused policies for
    :param managed_policy_details: A dictionary of managed policy and managed policy statement for an account
    :param access_advisor_data: A dictionary of access adivisor data per ARN, defaults to None
    :param force_refresh: Specifies whether we need to force-refresh each IAM role when we fetch it, defaults to False
    :param account_id: AWS Account ID, defaults to None
    :raises Exception: Raises an exception if there is a validation error
    :return: A dictionary of arn to its generated effective and unused policies.
    """

    if not access_advisor_data:
        if not account_id:
            raise Exception("Unable to retrieve access advisor data without account ID")

        access_advisor_data = await retrieve_json_data_from_redis_or_s3(
            s3_bucket=config.get_tenant_specific_key(
                "access_advisor.s3.bucket",
                tenant,
            ),
            s3_key=config.get_tenant_specific_key(
                "access_advisor.s3.file",
                tenant,
                "access_advisor/cache_access_advisor_{account_id}_v1.json.gz",
            ).format(account_id=account_id),
            tenant=tenant,
            max_age=86400,
        )

    minimum_age = config.get_tenant_specific_key(
        "aws.calculate_unused_policy_for_identities.max_unused_age", tenant, 90
    )
    ago = datetime.timedelta(minimum_age)
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    role_permissions_data = {}

    for arn in arns:
        if ":role/aws-service-role/" in arn:
            continue
        if ":role/aws-reserved" in arn:
            continue
        account_id = await get_resource_account(arn, tenant)
        role = await IAMRole.get(
            tenant,
            account_id,
            arn,
            force_refresh=force_refresh,
            run_sync=True,
        )
        role_dict = role.dict()
        role_name = role.name

        account_number = role.accountId

        # Get last-used data for role
        access_advisor_data_for_role = access_advisor_data.get(role.arn, [])
        used_services = set()
        unused_services = set()

        for service in access_advisor_data_for_role:
            (accessed, valid_authenticated) = get_epoch_authenticated(
                service["LastAuthenticated"]
            )

            if not accessed:
                unused_services.add(service["ServiceNamespace"])
                continue
            if not valid_authenticated:
                log.error(
                    "Got malformed Access Advisor data for {role_name} in {account_number} for service {service}"
                    ": {last_authenticated}".format(
                        role_name=role_name,
                        account_number=account_number,
                        service=service.get("ServiceNamespace"),
                        last_authenticated=service["LastAuthenticated"],
                    )
                )
                used_services.add(service["ServiceNamespace"])
                continue
            accessed_dt = datetime.datetime.fromtimestamp(
                accessed, tz=datetime.timezone.utc
            )
            if accessed_dt > now - ago:
                used_services.add(service["ServiceNamespace"])
            else:
                unused_services.add(service["ServiceNamespace"])

        # Generate Before/After for each role policy

        individual_role_inline_policy_changes = await calculate_policy_changes(
            role_dict, used_services, policy_type="inline_policy"
        )

        individual_role_managed_policy_changes = await calculate_policy_changes(
            role_dict,
            used_services,
            policy_type="managed_policy",
            managed_policy_details=managed_policy_details,
        )

        before_combined = await condense_statements(
            individual_role_inline_policy_changes["all_before_policy_statements"]
            + individual_role_managed_policy_changes["all_before_policy_statements"]
        )

        after_combined = await condense_statements(
            individual_role_inline_policy_changes["all_after_policy_statements"]
            + individual_role_managed_policy_changes["all_after_policy_statements"]
        )

        effective_policy = {"Statement": before_combined}
        effective_policy_unused_permissions_removed = {"Statement": after_combined}

        if len(json.dumps(after_combined)) > 10240:
            log.error(
                "After policy is too large: {}".format(len(json.dumps(after_combined)))
            )
            return

        permission_removal_commands = await generate_permission_removal_commands(
            tenant, role_dict, effective_policy_unused_permissions_removed
        )

        role_permissions_data[arn] = {
            "arn": arn,
            "tenant": tenant,
            "effective_policy": effective_policy,
            "effective_policy_unused_permissions_removed": effective_policy_unused_permissions_removed,
            "individual_role_inline_policy_changes": individual_role_inline_policy_changes,
            "individual_role_managed_policy_changes": individual_role_managed_policy_changes,
            "permission_removal_commands": permission_removal_commands,
        }

    return role_permissions_data
