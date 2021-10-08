import json
import sys
import time
from collections import defaultdict

from asgiref.sync import sync_to_async
from joblib import Parallel, delayed

from cloudumi_common.config import config
from cloudumi_common.lib.assume_role import ConsoleMeCloudAux, rate_limited, sts_conn
from cloudumi_common.lib.aws.aws_paginate import aws_paginated
from cloudumi_common.lib.cache import retrieve_json_data_from_redis_or_s3
from cloudumi_common.lib.redis import RedisHandler

log = config.get_logger(__name__)

ALL_IAM_MANAGED_POLICIES = defaultdict(dict)


@aws_paginated("AttachedPolicies")
def _get_user_managed_policies(user, client=None, **kwargs):
    return client.list_attached_user_policies(UserName=user["UserName"], **kwargs)


@rate_limited()
@sts_conn("iam", service_type="client")
def get_role_inline_policy_names(role, client=None, **kwargs):
    marker = {}
    inline_policies = []

    while True:
        response = client.list_role_policies(RoleName=role["RoleName"], **marker)
        inline_policies.extend(response["PolicyNames"])

        if response["IsTruncated"]:
            marker["Marker"] = response["Marker"]
        else:
            return inline_policies


@sts_conn("iam", service_type="client")
@rate_limited()
def get_role_inline_policy_document(role, policy_name, client=None, **kwargs):
    response = client.get_role_policy(RoleName=role["RoleName"], PolicyName=policy_name)
    return response.get("PolicyDocument")


def get_role_inline_policies(role, **kwargs):
    policy_names = get_role_inline_policy_names(role, **kwargs)

    policies = zip(
        policy_names,
        Parallel(n_jobs=20, backend="threading")(
            delayed(get_role_inline_policy_document)(role, policy_name, **kwargs)
            for policy_name in policy_names
        ),
    )
    policies = dict(policies)

    return policies


@sts_conn("iam", service_type="client")
@rate_limited()
def get_user_managed_policies(user, client=None, **kwargs):
    policies = _get_user_managed_policies(user, client=client, **kwargs)
    return [{"name": p["PolicyName"], "arn": p["PolicyArn"]} for p in policies]


@sts_conn("iam", service_type="client")
@aws_paginated("Tags")
@rate_limited()
def list_role_tags(role, client=None, **kwargs):
    return client.list_role_tags(RoleName=role["RoleName"], **kwargs)


@sts_conn("iam", service_type="client")
@rate_limited()
def get_user_managed_policy_documents(user, host, client=None, **kwargs):
    """Retrieve the currently active policy version document for every managed policy that is attached to the user."""
    policies = get_user_managed_policies(user, force_client=client)

    policy_names = (policy["name"] for policy in policies)
    delayed_gmpd_calls = (
        delayed(get_managed_policy_document)(
            policy["arn"], host=host, force_client=client
        )
        for policy in policies
    )
    policy_documents = Parallel(n_jobs=20, backend="threading")(delayed_gmpd_calls)

    return dict(zip(policy_names, policy_documents))


@sts_conn("iam", service_type="client")
@rate_limited()
def get_role_managed_policies(role, client=None, **kwargs):
    marker = {}
    policies = []

    while True:
        response = client.list_attached_role_policies(
            RoleName=role["RoleName"], **marker
        )
        policies.extend(response["AttachedPolicies"])

        if response["IsTruncated"]:
            marker["Marker"] = response["Marker"]
        else:
            break

    return [{"name": p["PolicyName"], "arn": p["PolicyArn"]} for p in policies]


@sts_conn("iam", service_type="client")
@rate_limited()
def get_role_managed_policy_documents(role, client=None, **kwargs):
    """Retrieve the currently active policy version document for every managed policy that is attached to the role."""
    policies = get_role_managed_policies(role, force_client=client)

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
def create_managed_policy(cloudaux, name, path, policy, description, host):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "cloudaux": cloudaux,
        "name": name,
        "path": path,
        "policy": policy,
        "description": "description",
        "message": "Creating Managed Policy",
        "host": host,
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
    versions = await sync_to_async(cloudaux.call)(
        "iam.client.list_policy_versions", PolicyArn=policy_arn
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
        await sync_to_async(cloudaux.call)(
            "iam.client.delete_policy_version",
            PolicyArn=policy_arn,
            VersionId=current_policy_versions.pop(pop_position)["VersionId"],
        )

    await sync_to_async(cloudaux.call)(
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
    host,
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
        "host": host,
    }

    ca = await sync_to_async(ConsoleMeCloudAux)(**conn_details)

    if not existing_policy:
        log_data["message"] = "Policy does not exist. Creating"
        log.debug(log_data)
        await sync_to_async(create_managed_policy)(
            ca, policy_name, policy_path, new_policy, description, host
        )
        return

    log_data["message"] = "Policy exists and needs to be updated"
    log.debug(log_data)
    # Update the managed policy
    await update_managed_policy(ca, policy_name, new_policy, policy_arn)


async def get_all_iam_managed_policies_for_account(account_id, host):
    global ALL_IAM_MANAGED_POLICIES
    # TODO: Use redis clusters for this type of thing and not a global var
    policy_key: str = config.get_host_specific_key(
        f"site_configs.{host}.redis.iam_managed_policies_key",
        host,
        f"{host}_IAM_MANAGED_POLICIES",
    )
    current_time = time.time()
    if current_time - ALL_IAM_MANAGED_POLICIES[host].get("last_update", 0) > 500:
        red = await RedisHandler().redis(host)
        ALL_IAM_MANAGED_POLICIES[host]["managed_policies"] = await sync_to_async(
            red.hgetall
        )(policy_key)
        ALL_IAM_MANAGED_POLICIES[host]["last_update"] = current_time

    if ALL_IAM_MANAGED_POLICIES[host].get("managed_policies"):
        return json.loads(
            ALL_IAM_MANAGED_POLICIES[host]["managed_policies"].get(account_id, "[]")
        )
    else:
        s3_bucket = config.get_host_specific_key(
            f"site_configs.{host}.account_resource_cache.s3.bucket", host
        )
        s3_key = config.get_host_specific_key(
            f"site_configs.{host}.account_resource_cache.s3.file",
            host,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="managed_policies", account_id=account_id)
        return await retrieve_json_data_from_redis_or_s3(
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            default=[],
            host=host,
        )
