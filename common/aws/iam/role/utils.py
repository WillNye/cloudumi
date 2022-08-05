import asyncio
import sys
from typing import Any, Dict, Optional

import sentry_sdk
from botocore.exceptions import ClientError
from joblib import Parallel, delayed

import common.lib.noq_json as json
from common.aws.iam.role.config import (
    get_active_tear_users_tag,
    get_tear_support_groups_tag,
)
from common.aws.iam.utils import get_tenant_iam_conn
from common.config import config, models
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.assume_role import rate_limited, sts_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.aws_paginate import aws_paginated
from common.lib.cloud_credential_authorization_mapping import RoleAuthorizations
from common.lib.plugins import get_plugin_by_name
from common.models import (
    CloneRoleRequestModel,
    HubAccount,
    PrincipalModelRoleAccessConfig,
    PrincipalModelTearConfig,
    RoleCreationRequestModel,
)

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


def _get_iam_role_sync(
    account_id, role_name, conn, tenant: str
) -> Optional[Dict[str, Any]]:
    client = get_tenant_iam_conn(tenant, account_id, "noq_get_iam_role", read_only=True)
    role = client.get_role(RoleName=role_name)["Role"]
    role["ManagedPolicies"] = get_role_managed_policies(
        {"RoleName": role_name}, tenant=tenant, **conn
    )
    role["InlinePolicies"] = get_role_inline_policies(
        {"RoleName": role_name}, tenant=tenant, **conn
    )
    role["Tags"] = list_role_tags({"RoleName": role_name}, tenant=tenant, **conn)
    return role


async def _get_iam_role_async(
    account_id, role_name, conn, tenant: str
) -> Optional[Dict[str, Any]]:
    tasks = []
    client = await aio_wrapper(
        get_tenant_iam_conn,
        tenant,
        account_id,
        "noq_get_iam_role",
        read_only=True,
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
                get_role_managed_policies,
                {"RoleName": role_name},
                tenant=tenant,
                **conn,
            ),
        ),
        loop.run_in_executor(
            executor,
            functools.partial(
                get_role_inline_policies, {"RoleName": role_name}, tenant=tenant, **conn
            ),
        ),
    ]
    # completed, pending = await asyncio.wait(tasks)
    # results = [t.result() for t in completed]
    results = await asyncio.gather(*tasks)
    # results = await run_io_tasks_in_parallel_v2(executor, [
    #     lambda: {"Role": client.get_role(RoleName=role_name)},
    #     lambda: {"ManagedPolicies": get_role_managed_policies({"RoleName": role_name}, tenant=tenant, **conn)},
    #     lambda: {"InlinePolicies": get_role_inline_policies({"RoleName": role_name}, tenant=tenant, **conn)},
    #     lambda: {"Tags": list_role_tags({"RoleName": role_name}, tenant=tenant, **conn)}]
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
    create_model: RoleCreationRequestModel, username: str, tenant: str
):
    """
    Creates IAM role.
    :param create_model: RoleCreationRequestModel, which has the following attributes:
        account_id: destination account's ID
        role_name: destination role name
        description: optional string - description of the role
                     default: Role created by {username} through Noq
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
        "tenant": tenant,
    }
    log.info(log_data)

    default_trust_policy = config.get_tenant_specific_key(
        "user_role_creator.default_trust_policy",
        tenant,
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

    default_max_session_duration = config.get_tenant_specific_key(
        "user_role_creator.default_max_session_duration", tenant, 3600
    )

    if create_model.description:
        description = create_model.description
    else:
        description = f"Role created by {username} through Noq"

    iam_client = await aio_wrapper(
        get_tenant_iam_conn, tenant, create_model.account_id, f"create_role_{username}"
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
            "tenant": tenant,
        },
    )
    log_data["message"] = "Successfully created role"
    log.info(log_data)

    return results


async def _fetch_role_resource(account_id, role_name, tenant, user):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to fetch role details",
        "account": account_id,
        "role": role_name,
    }
    log.info(log_data)
    iam_resource = await aio_wrapper(
        get_tenant_iam_conn,
        tenant,
        account_id,
        "_fetch_role_resource",
        user=user,
        service_type="resource",
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


async def _delete_iam_role(account_id, role_name, username, tenant):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Attempting to delete role",
        "account_id": account_id,
        "role_name": role_name,
        "user": username,
        "tenant": tenant,
    }
    log.info(log_data)
    role = await _fetch_role_resource(account_id, role_name, tenant, username)

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
            "tenant": tenant,
        },
    )


async def _clone_iam_role(clone_model: CloneRoleRequestModel, username, tenant):
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
                default: False - uses default Noq AssumeRolePolicy
            tags: bool
                default: False - defaults to no tags
            copy_description: bool
                default: False - defaults to copying provided description or default description
            description: string
                default: "Role cloned via Noq by `username` from `arn:aws:iam::<account_id>:role/<role_name>`
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
        "tenant": tenant,
    }
    log.info(log_data)
    role = await _fetch_role_resource(
        clone_model.account_id, clone_model.role_name, tenant, username
    )

    default_trust_policy = config.get_tenant_specific_key(
        "user_role_creator.default_trust_policy", tenant
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

    default_max_session_duration = config.get_tenant_specific_key(
        "user_role_creator.default_max_session_duration", tenant, 3600
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
        description = f"Role cloned via Noq by {username} from {role.arn}"

    tags = role.tags if clone_model.options.tags and role.tags else []
    iam_client = await aio_wrapper(
        get_tenant_iam_conn,
        tenant,
        clone_model.dest_account_id,
        f"clone_role_{username}",
        user=username,
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
        clone_model.dest_account_id, clone_model.dest_role_name, tenant, username
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
            "tenant": tenant,
        },
    )
    log_data["message"] = "Successfully cloned role"
    log.info(log_data)
    return results


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
@aws_paginated("Tags")
@rate_limited()
def list_role_tags(role, client=None, **kwargs):
    return client.list_role_tags(RoleName=role["RoleName"], **kwargs)


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
    from common.aws.iam.policy.utils import get_managed_policy_document

    policies = get_role_managed_policies(role, force_client=client)
    policy_names = (policy["name"] for policy in policies)
    delayed_gmpd_calls = (
        delayed(get_managed_policy_document)(policy["arn"], force_client=client)
        for policy in policies
    )
    policy_documents = Parallel(n_jobs=20, backend="threading")(delayed_gmpd_calls)

    return dict(zip(policy_names, policy_documents))


async def update_role_tear_config(
    tenant, user, role_name, account_id: str, tear_config: PrincipalModelTearConfig
) -> [bool, str]:
    from common.aws.iam.role.models import IAMRole

    client = await aio_wrapper(
        get_tenant_iam_conn,
        tenant,
        account_id,
        "update_role_tear_config",
        user=user,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    try:
        await aio_wrapper(
            client.tag_role,
            RoleName=role_name,
            Tags=[
                {
                    "Key": get_active_tear_users_tag(tenant),
                    "Value": ":".join(tear_config.active_users),
                },
                {
                    "Key": get_tear_support_groups_tag(tenant),
                    "Value": ":".join(tear_config.supported_groups),
                },
            ],
        )
    except Exception as err:
        return False, repr(err)
    else:
        await IAMRole.get(
            tenant, account_id, f"arn:aws:iam::{account_id}:role/{role_name}", True
        )
        return True, ""


async def update_assume_role_policy_trust_noq(tenant, user, role_name, account_id):
    client = await aio_wrapper(
        get_tenant_iam_conn,
        tenant,
        account_id,
        "noq_update_assume_role_policy_trust",
        user=user,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    role = await aio_wrapper(client.get_role, RoleName=role_name)
    assume_role_trust_policy = role.get("Role", {}).get("AssumeRolePolicyDocument", {})
    if not assume_role_trust_policy:
        return False
    hub_account = (
        models.ModelAdapter(HubAccount).load_config("hub_account", tenant).model
    )
    if not hub_account:
        return False

    assume_role_policy = {
        "Effect": "Allow",
        "Action": ["sts:AssumeRole", "sts:TagSession"],
        "Principal": {"AWS": [hub_account.role_arn]},
    }

    assume_role_trust_policy["Statement"].append(assume_role_policy)

    client.update_assume_role_policy(
        RoleName=role_name, PolicyDocument=json.dumps(assume_role_trust_policy)
    )
    return True


async def get_authorized_group_map(
    authorization_mapping: Dict[str, RoleAuthorizations], tenant
) -> Dict[str, RoleAuthorizations]:
    from common.aws.iam.role.models import IAMRole

    required_trust_policy_entity = config.get_tenant_specific_key(
        "cloud_credential_authorization_mapping.role_tags.required_trust_policy_entity",
        tenant,
    )

    for iam_role in await IAMRole.query(tenant):
        if (
            required_trust_policy_entity
            and required_trust_policy_entity.lower()
            not in json.dumps(
                iam_role.policy["AssumeRolePolicyDocument"],
            ).lower()
        ):
            continue

        role_tag_config = "cloud_credential_authorization_mapping.role_tags"
        authorized_group_tags = config.get_tenant_specific_key(
            f"{role_tag_config}.authorized_groups_tags", tenant, []
        )
        authorized_cli_group_tags = config.get_tenant_specific_key(
            f"{role_tag_config}.authorized_groups_cli_only_tags", tenant, []
        )

        for tag in iam_role.tags:
            if not tag["Value"]:
                continue
            if tag["Key"] in authorized_group_tags:
                splitted_groups = tag["Value"].split(":")
                for group in splitted_groups:
                    if config.get_tenant_specific_key(
                        "auth.force_groups_lowercase",
                        tenant,
                        False,
                    ):
                        group = group.lower()
                    if not authorization_mapping.get(group):
                        authorization_mapping[group] = RoleAuthorizations.parse_obj(
                            {
                                "authorized_roles": set(),
                                "authorized_roles_cli_only": set(),
                            }
                        )
                    authorization_mapping[group].authorized_roles.add(iam_role.arn)
            if tag["Key"] in authorized_cli_group_tags:
                splitted_groups = tag["Value"].split(":")
                for group in splitted_groups:
                    if config.get_tenant_specific_key(
                        "auth.force_groups_lowercase",
                        tenant,
                        False,
                    ):
                        group = group.lower()
                    if not authorization_mapping.get(group):
                        authorization_mapping[group] = RoleAuthorizations.parse_obj(
                            {
                                "authorized_roles": set(),
                                "authorized_roles_cli_only": set(),
                            }
                        )
                    authorization_mapping[group].authorized_roles_cli_only.add(
                        iam_role.arn
                    )
    return authorization_mapping


async def get_roles_as_resource(
    tenant: str, viewable_accounts: set, resource_map: dict
):
    from common.aws.iam.role.models import IAMRole

    account_map = await get_account_id_to_name_mapping(tenant)

    iam_roles = await IAMRole.query(
        tenant,
        filter_condition=IAMRole.accountId.is_in(*viewable_accounts),
        attributes_to_get=["accountId", "arn", "templated"],
    )
    for iam_role in iam_roles:
        resource_map[iam_role.arn] = {
            "account_id": iam_role.accountId,
            "arn": iam_role.arn,
            "account_name": account_map.get(iam_role.accountId, "N/A"),
            "technology": "AWS::IAM::Role",
            "templated": iam_role.templated,
        }

    return resource_map


async def update_role_access_config(
    tenant,
    user,
    role_name,
    account_id: str,
    role_access_config: PrincipalModelRoleAccessConfig,
) -> [bool, str]:
    client = await aio_wrapper(
        get_tenant_iam_conn,
        tenant,
        account_id,
        "update_role_access_config",
        user=user,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )
    tags_to_update = []

    for group_tag in role_access_config.noq_authorized_cli_groups:
        tags_to_update.append(
            {
                "Key": group_tag["tag_name"],
                "Value": ":".join(group_tag["value"]),
            }
        )

    for group_tag in role_access_config.noq_authorized_groups:
        tags_to_update.append(
            {
                "Key": group_tag["tag_name"],
                "Value": ":".join(group_tag["value"]),
            }
        )

    try:
        await aio_wrapper(
            client.tag_role,
            RoleName=role_name,
            Tags=tags_to_update,
        )
        return True, ""
    except Exception as err:
        return False, repr(err)
