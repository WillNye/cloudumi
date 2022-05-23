import asyncio
import sys
from typing import Any, Dict, Optional

import sentry_sdk
import ujson as json
from botocore.exceptions import ClientError

from common.aws.iam.utils import get_host_iam_conn
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.iam import (
    get_role_inline_policies,
    get_role_managed_policies,
    list_role_tags,
)
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.plugins import get_plugin_by_name
from common.models import CloneRoleRequestModel, RoleCreationRequestModel, SpokeAccount

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


def _get_iam_role_sync(
    account_id, role_name, conn, host: str
) -> Optional[Dict[str, Any]]:
    client = get_host_iam_conn(host, account_id, "consoleme_get_iam_role")
    role = client.get_role(RoleName=role_name)["Role"]
    role["ManagedPolicies"] = get_role_managed_policies(
        {"RoleName": role_name}, host=host, **conn
    )
    role["InlinePolicies"] = get_role_inline_policies(
        {"RoleName": role_name}, host=host, **conn
    )
    role["Tags"] = list_role_tags({"RoleName": role_name}, host=host, **conn)
    return role


async def _get_iam_role_async(
    account_id, role_name, conn, host: str
) -> Optional[Dict[str, Any]]:
    tasks = []
    client = await aio_wrapper(
        get_host_iam_conn, host, account_id, "consoleme_get_iam_role"
    )
    role_details = asyncio.ensure_future(
        aio_wrapper(client.get_role, RoleName=role_name)
    )
    tasks.append(role_details)
    # executor = ThreadPoolExecutor(max_workers=os.cpu_count())
    # futures = []
    # all_tasks = [
    #     get_role_managed_policies,
    #     get_role_inline_policies,
    #     list_role_tags,
    # ]

    import concurrent.futures

    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=4,
    )
    import functools

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(
            executor, functools.partial(client.get_role, RoleName=role_name)
        ),
        loop.run_in_executor(
            executor,
            functools.partial(
                get_role_managed_policies, {"RoleName": role_name}, host=host, **conn
            ),
        ),
        loop.run_in_executor(
            executor,
            functools.partial(
                get_role_inline_policies, {"RoleName": role_name}, host=host, **conn
            ),
        ),
    ]
    # completed, pending = await asyncio.wait(tasks)
    # results = [t.result() for t in completed]
    results = await asyncio.gather(*tasks)
    # results = await run_io_tasks_in_parallel_v2(executor, [
    #     lambda: {"Role": client.get_role(RoleName=role_name)},
    #     lambda: {"ManagedPolicies": get_role_managed_policies({"RoleName": role_name}, host=host, **conn)},
    #     lambda: {"InlinePolicies": get_role_inline_policies({"RoleName": role_name}, host=host, **conn)},
    #     lambda: {"Tags": list_role_tags({"RoleName": role_name}, host=host, **conn)}]
    #
    # )

    role = results[0]["Role"]
    role["ManagedPolicies"] = results[1]
    role["InlinePolicies"] = results[2]

    # role = {}
    #
    # for d in results:
    #     if d.get("Role"):
    #         role.update(d["Role"]["Role"])
    #     else:
    #         role.update(d)

    return role


async def _create_iam_role(
    create_model: RoleCreationRequestModel, username: str, host: str
):
    """
    Creates IAM role.
    :param create_model: RoleCreationRequestModel, which has the following attributes:
        account_id: destination account's ID
        role_name: destination role name
        description: optional string - description of the role
                     default: Role created by {username} through ConsoleMe
        instance_profile: optional boolean - whether to create an instance profile and attach it to the role or not
                     default: True
    :param username: username of user requesting action
    :return: results: - indicating the results of each action
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to create role",
        "account_id": create_model.account_id,
        "role_name": create_model.role_name,
        "user": username,
        "host": host,
    }
    log.info(log_data)

    default_trust_policy = config.get_host_specific_key(
        "user_role_creator.default_trust_policy",
        host,
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        },
    )
    if default_trust_policy is None:
        raise MissingConfigurationValue(
            "Missing Default Assume Role Policy Configuration"
        )

    default_max_session_duration = config.get_host_specific_key(
        "user_role_creator.default_max_session_duration", host, 3600
    )

    if create_model.description:
        description = create_model.description
    else:
        description = f"Role created by {username} through ConsoleMe"

    iam_client = await aio_wrapper(
        get_host_iam_conn, host, create_model.account_id, f"create_role_{username}"
    )

    results = {"errors": 0, "role_created": "false", "action_results": []}
    try:
        await aio_wrapper(
            iam_client.create_role,
            RoleName=create_model.role_name,
            AssumeRolePolicyDocument=json.dumps(default_trust_policy),
            MaxSessionDuration=default_max_session_duration,
            Description=description,
            Tags=[],
        )
        results["action_results"].append(
            {
                "status": "success",
                "message": f"Role arn:aws:iam::{create_model.account_id}:role/{create_model.role_name} "
                f"successfully created",
            }
        )
        results["role_created"] = "true"
    except Exception as e:
        log_data["message"] = "Exception occurred creating role"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        results["action_results"].append(
            {
                "status": "error",
                "message": f"Error creating role {create_model.role_name} in account {create_model.account_id}:"
                + str(e),
            }
        )
        results["errors"] += 1
        sentry_sdk.capture_exception()
        # Since we were unable to create the role, no point continuing, just return
        return results

    # If here, role has been successfully created, add status updates for each action
    results["action_results"].append(
        {
            "status": "success",
            "message": "Successfully added default Assume Role Policy Document",
        }
    )
    results["action_results"].append(
        {
            "status": "success",
            "message": "Successfully added description: " + description,
        }
    )

    # Create instance profile and attach if specified
    if create_model.instance_profile:
        try:
            await aio_wrapper(
                iam_client.create_instance_profile,
                InstanceProfileName=create_model.role_name,
            )
            await aio_wrapper(
                iam_client.add_role_to_instance_profile,
                InstanceProfileName=create_model.role_name,
                RoleName=create_model.role_name,
            )
            results["action_results"].append(
                {
                    "status": "success",
                    "message": f"Successfully added instance profile {create_model.role_name} to role "
                    f"{create_model.role_name}",
                }
            )
        except Exception as e:
            log_data[
                "message"
            ] = "Exception occurred creating/attaching instance profile"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            results["action_results"].append(
                {
                    "status": "error",
                    "message": f"Error creating/attaching instance profile {create_model.role_name} to role: "
                    + str(e),
                }
            )
            results["errors"] += 1

    stats.count(
        f"{log_data['function']}.success",
        tags={
            "role_name": create_model.role_name,
            "host": host,
        },
    )
    log_data["message"] = "Successfully created role"
    log.info(log_data)

    return results


async def _fetch_role_resource(account_id, role_name, host, user):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to fetch role details",
        "account": account_id,
        "role": role_name,
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
        session_name=sanitize_session_name("_fetch_role_resource"),
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )
    try:
        iam_role = await aio_wrapper(iam_resource.Role, role_name)
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "NoSuchEntity":
            log_data["message"] = "Requested role doesn't exist"
            log.error(log_data)
        raise
    await aio_wrapper(iam_role.load)
    return iam_role


async def _delete_iam_role(account_id, role_name, username, host) -> bool:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to delete role",
        "account_id": account_id,
        "role_name": role_name,
        "user": username,
        "host": host,
    }
    log.info(log_data)
    role = await _fetch_role_resource(account_id, role_name, host, username)

    for instance_profile in await aio_wrapper(role.instance_profiles.all):
        await aio_wrapper(instance_profile.load)
        log.info(
            {
                **log_data,
                "message": "Removing and deleting instance profile from role",
                "instance_profile": instance_profile.name,
            }
        )
        await aio_wrapper(instance_profile.remove_role, RoleName=role.name)
        await aio_wrapper(instance_profile.delete)

    # Detach managed policies
    for policy in await aio_wrapper(role.attached_policies.all):
        await aio_wrapper(policy.load)
        log.info(
            {
                **log_data,
                "message": "Detaching managed policy from role",
                "policy_arn": policy.arn,
            }
        )
        await aio_wrapper(policy.detach_role, RoleName=role_name)

    # Delete Inline policies
    for policy in await aio_wrapper(role.policies.all):
        await aio_wrapper(policy.load)
        log.info(
            {
                **log_data,
                "message": "Deleting inline policy on role",
                "policy_name": policy.name,
            }
        )
        await aio_wrapper(policy.delete)

    log.info({**log_data, "message": "Performing role deletion"})
    await aio_wrapper(role.delete)
    stats.count(
        f"{log_data['function']}.success",
        tags={
            "role_name": role_name,
            "host": host,
        },
    )


async def clone_iam_role(clone_model: CloneRoleRequestModel, username, host):
    """
    Clones IAM role within same account or across account, always creating and attaching instance profile if one exists
    on the source role.
    ;param username: username of user requesting action
    ;:param clone_model: CloneRoleRequestModel, which has the following attributes:
        account_id: source role's account ID
        role_name: source role's name
        dest_account_id: destination role's account ID (may be same as account_id)
        dest_role_name: destination role's name
        clone_options: dict to indicate what to copy when cloning:
            assume_role_policy: bool
                default: False - uses default ConsoleMe AssumeRolePolicy
            tags: bool
                default: False - defaults to no tags
            copy_description: bool
                default: False - defaults to copying provided description or default description
            description: string
                default: "Role cloned via ConsoleMe by `username` from `arn:aws:iam::<account_id>:role/<role_name>`
                if copy_description is True, then description is ignored
            inline_policies: bool
                default: False - defaults to no inline policies
            managed_policies: bool
                default: False - defaults to no managed policies
    :return: results: - indicating the results of each action
    """

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to clone role",
        "account_id": clone_model.account_id,
        "role_name": clone_model.role_name,
        "dest_account_id": clone_model.dest_account_id,
        "dest_role_name": clone_model.dest_role_name,
        "user": username,
        "host": host,
    }
    log.info(log_data)
    role = await _fetch_role_resource(
        clone_model.account_id, clone_model.role_name, host, username
    )

    default_trust_policy = config.get_host_specific_key(
        "user_role_creator.default_trust_policy", host
    )
    trust_policy = (
        role.assume_role_policy_document
        if clone_model.options.assume_role_policy
        else default_trust_policy
    )
    if trust_policy is None:
        raise MissingConfigurationValue(
            "Missing Default Assume Role Policy Configuration"
        )

    default_max_session_duration = config.get_host_specific_key(
        "user_role_creator.default_max_session_duration", host, 3600
    )

    max_session_duration = (
        role.max_session_duration
        if clone_model.options.max_session_duration
        else default_max_session_duration
    )

    if (
        clone_model.options.copy_description
        and role.description is not None
        and role.description != ""
    ):
        description = role.description
    elif (
        clone_model.options.description is not None
        and clone_model.options.description != ""
    ):
        description = clone_model.options.description
    else:
        description = f"Role cloned via ConsoleMe by {username} from {role.arn}"

    tags = role.tags if clone_model.options.tags and role.tags else []

    iam_client = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        host,
        username,
        service_type="client",
        account_number=clone_model.dest_account_id,
        region=config.region,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": clone_model.dest_account_id})
        .first.name,
        session_name=sanitize_session_name("clone_role_" + username),
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )
    results = {"errors": 0, "role_created": "false", "action_results": []}
    try:
        await aio_wrapper(
            iam_client.create_role,
            RoleName=clone_model.dest_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            MaxSessionDuration=max_session_duration,
            Description=description,
            Tags=tags,
        )
        results["action_results"].append(
            {
                "status": "success",
                "message": f"Role arn:aws:iam::{clone_model.dest_account_id}:role/{clone_model.dest_role_name} "
                f"successfully created",
            }
        )
        results["role_created"] = "true"
    except Exception as e:
        log_data["message"] = "Exception occurred creating cloned role"
        log_data["error"] = str(e)
        log.error(log_data, exc_info=True)
        results["action_results"].append(
            {
                "status": "error",
                "message": f"Error creating role {clone_model.dest_role_name} in account {clone_model.dest_account_id}:"
                + str(e),
            }
        )
        results["errors"] += 1
        sentry_sdk.capture_exception()
        # Since we were unable to create the role, no point continuing, just return
        return results

    if clone_model.options.tags:
        results["action_results"].append(
            {"status": "success", "message": "Successfully copied tags"}
        )
    if clone_model.options.assume_role_policy:
        results["action_results"].append(
            {
                "status": "success",
                "message": "Successfully copied Assume Role Policy Document",
            }
        )
    else:
        results["action_results"].append(
            {
                "status": "success",
                "message": "Successfully added default Assume Role Policy Document",
            }
        )
    if (
        clone_model.options.copy_description
        and role.description is not None
        and role.description != ""
    ):
        results["action_results"].append(
            {"status": "success", "message": "Successfully copied description"}
        )
    elif clone_model.options.copy_description:
        results["action_results"].append(
            {
                "status": "error",
                "message": "Failed to copy description, so added default description: "
                + description,
            }
        )
    else:
        results["action_results"].append(
            {
                "status": "success",
                "message": "Successfully added description: " + description,
            }
        )
    # Create instance profile and attach if it exists in source role
    if len(list(await aio_wrapper(role.instance_profiles.all))) > 0:
        try:
            await aio_wrapper(
                iam_client.create_instance_profile,
                InstanceProfileName=clone_model.dest_role_name,
            )
            await aio_wrapper(
                iam_client.add_role_to_instance_profile,
                InstanceProfileName=clone_model.dest_role_name,
                RoleName=clone_model.dest_role_name,
            )
            results["action_results"].append(
                {
                    "status": "success",
                    "message": f"Successfully added instance profile {clone_model.dest_role_name} to role "
                    f"{clone_model.dest_role_name}",
                }
            )
        except Exception as e:
            log_data[
                "message"
            ] = "Exception occurred creating/attaching instance profile"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            sentry_sdk.capture_exception()
            results["action_results"].append(
                {
                    "status": "error",
                    "message": f"Error creating/attaching instance profile {clone_model.dest_role_name} to role: "
                    + str(e),
                }
            )
            results["errors"] += 1

    # other optional attributes to copy over after role has been successfully created

    cloned_role = await _fetch_role_resource(
        clone_model.dest_account_id, clone_model.dest_role_name, host, username
    )

    # Copy inline policies
    if clone_model.options.inline_policies:
        for src_policy in await aio_wrapper(role.policies.all):
            await aio_wrapper(src_policy.load)
            try:
                dest_policy = await aio_wrapper(cloned_role.Policy, src_policy.name)
                await aio_wrapper(
                    dest_policy.put,
                    PolicyDocument=json.dumps(src_policy.policy_document),
                )
                results["action_results"].append(
                    {
                        "status": "success",
                        "message": f"Successfully copied inline policy {src_policy.name}",
                    }
                )
            except Exception as e:
                log_data["message"] = "Exception occurred copying inline policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()
                results["action_results"].append(
                    {
                        "status": "error",
                        "message": f"Error copying inline policy {src_policy.name}: "
                        + str(e),
                    }
                )
                results["errors"] += 1

    # Copy managed policies
    if clone_model.options.managed_policies:
        for src_policy in await aio_wrapper(role.attached_policies.all):
            await aio_wrapper(src_policy.load)
            dest_policy_arn = src_policy.arn.replace(
                clone_model.account_id, clone_model.dest_account_id
            )
            try:
                await aio_wrapper(cloned_role.attach_policy, PolicyArn=dest_policy_arn)
                results["action_results"].append(
                    {
                        "status": "success",
                        "message": f"Successfully attached managed policy {src_policy.arn} as {dest_policy_arn}",
                    }
                )
            except Exception as e:
                log_data["message"] = "Exception occurred copying managed policy"
                log_data["error"] = str(e)
                log.error(log_data, exc_info=True)
                sentry_sdk.capture_exception()
                results["action_results"].append(
                    {
                        "status": "error",
                        "message": f"Error attaching managed policy {dest_policy_arn}: "
                        + str(e),
                    }
                )
                results["errors"] += 1

    stats.count(
        f"{log_data['function']}.success",
        tags={
            "role_name": clone_model.role_name,
            "host": host,
        },
    )
    log_data["message"] = "Successfully cloned role"
    log.info(log_data)
    return results


def apply_managed_policy_to_role(
    role: Dict, policy_name: str, session_name: str, host: str, user: str
) -> bool:
    """
    Apply a managed policy to a role.
    :param role: An AWS role dictionary (from a boto3 get_role or get_account_authorization_details call)
    :param policy_name: Name of managed policy to add to role
    :param session_name: Name of session to assume role with. This is an identifier that will be logged in CloudTrail
    :param host: The NOQ Tenant
    :param user: The user who is applying the manage policy to the role
    :return:
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "role": role,
        "policy_name": policy_name,
        "session_name": session_name,
    }
    account_id = role.get("Arn").split(":")[4]
    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
    client = boto3_cached_conn(
        "iam",
        host,
        user,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        session_name=sanitize_session_name(session_name),
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )

    client.attach_role_policy(RoleName=role.get("RoleName"), PolicyArn=policy_arn)
    log_data["message"] = "Applied managed policy to role"
    log.debug(log_data)
    stats.count(
        f"{function}.attach_role_policy",
        tags={
            "role": role.get("Arn"),
            "policy": policy_arn,
            "host": host,
        },
    )
    return True


async def fetch_assume_role_policy(
    role_arn: str, host: str, user: str
) -> Optional[Dict]:
    account_id = role_arn.split(":")[4]
    role_name = role_arn.split("/")[-1]
    try:
        role = await _fetch_role_resource(account_id, role_name, host, user)
    except ClientError:
        # Role is most likely on an account that we do not have access to
        sentry_sdk.capture_exception()
        return None
    return role.assume_role_policy_document
