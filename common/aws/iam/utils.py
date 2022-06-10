import copy
import json
import os
import pathlib

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
    if service == resource_type:
        resource_type = "all"
    return RESOURCE_PERMISSION_MAP[service][resource_type]


def get_host_iam_conn(
    host: str, account_id: str, session_name: str, user: str = None, **kwargs
):
    return boto3_cached_conn(
        "iam",
        host,
        user,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
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
