import copy
import json
import os
import pathlib
from typing import Optional

from common.aws.iam.user.utils import fetch_iam_user
from common.config import config
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.aws.sanitize import sanitize_session_name
from common.models import SpokeAccount

with open(
    os.path.join(
        pathlib.Path(__file__).parent.resolve(), "aws_resource_permission_map.json"
    )
) as f:
    RESOURCE_PERMISSION_MAP = json.load(f)


def get_supported_resource_permissions(service: str, resource_type: str = "all"):
    permission_map = RESOURCE_PERMISSION_MAP[service]
    if service == resource_type:
        # If only one resource type exists, return the permissions for that resource type.
        svc_resource_types = [srt for srt in permission_map.keys() if srt != "all"]
        return (
            permission_map["all"]
            if len(svc_resource_types) != 1
            else permission_map[svc_resource_types[0]]
        )
    return permission_map[resource_type]


def get_tenant_iam_conn(
    tenant: str, account_id: str, session_name: str, user: str = None, **kwargs
):
    return boto3_cached_conn(
        "iam",
        tenant,
        user,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name,
        retry_max_attempts=2,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        session_name=sanitize_session_name(session_name),
        **kwargs
    )


async def _cloudaux_to_aws(principal):
    """Convert the cloudaux get_role/get_user into the get_account_authorization_details equivalent."""
    # Pop out the fields that are not required:
    # Arn and RoleName/UserName will be popped off later:
    unrequired_fields = ["_version", "MaxSessionDuration"]
    principal_type = principal["Arn"].split(":")[-1].split("/")[0]
    for uf in unrequired_fields:
        principal.pop(uf, None)

    # Fix the Managed Policies:
    principal["AttachedManagedPolicies"] = list(
        map(
            lambda x: {"PolicyName": x["name"], "PolicyArn": x["arn"]},
            principal.get("ManagedPolicies", []),
        )
    )
    principal.pop("ManagedPolicies", None)

    # Fix the tags:
    if isinstance(principal.get("Tags", {}), dict):
        principal["Tags"] = list(
            map(
                lambda key: {"Key": key, "Value": principal["Tags"][key]},
                principal.get("Tags", {}),
            )
        )

    # Note: the instance profile list is verbose -- not transforming it (outside of renaming the field)!
    principal["InstanceProfileList"] = principal.pop("InstanceProfiles", [])

    # Inline Policies:
    if principal_type == "role":

        principal["RolePolicyList"] = list(
            map(
                lambda name: {
                    "PolicyName": name,
                    "PolicyDocument": principal["InlinePolicies"][name],
                },
                principal.get("InlinePolicies", {}),
            )
        )
    else:
        principal["UserPolicyList"] = copy.deepcopy(principal.pop("InlinePolicies", []))
    principal.pop("InlinePolicies", None)

    return principal


async def get_iam_principal_owner(arn: str, tenant: str) -> Optional[str]:
    from common.aws.iam.role.models import IAMRole
    from common.aws.utils import ResourceSummary

    principal_details = {}
    resource_summary = await ResourceSummary.set(tenant, arn)
    principal_type = resource_summary.resource_type
    account_id = resource_summary.account
    # trying to find principal for subsequent queries
    if principal_type == "role":
        principal_details = (await IAMRole.get(tenant, account_id, arn)).dict()
    elif principal_type == "user":
        principal_details = await fetch_iam_user(account_id, arn, tenant)
    return principal_details.get("owner")
