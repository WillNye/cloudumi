import asyncio
import sys
from typing import Any, Dict, Optional

import sentry_sdk
import ujson as json

from common.aws.iam.utils import get_host_iam_conn
from common.config import config
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.asyncio import aio_wrapper
from common.lib.aws.iam import (
    get_role_inline_policies,
    get_role_managed_policies,
    list_role_tags,
)
from common.lib.plugins import get_plugin_by_name
from common.models import RoleCreationRequestModel

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


async def _create_iam_role(create_model: RoleCreationRequestModel, username, host):
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
