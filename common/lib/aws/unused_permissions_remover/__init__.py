import datetime
from typing import Any, Dict, List, Optional

import sentry_sdk
import ujson as json
from jinja2 import Environment, FileSystemLoader
from jinja2.utils import select_autoescape

from common.aws.iam.role.models import IAMRole
from common.aws.iam.role.utils import get_role_managed_policy_documents
from common.config import config
from common.lib.asyncio import aio_wrapper
from common.lib.aws.access_advisor import get_epoch_authenticated
from common.lib.aws.utils import (
    calculate_policy_changes,
    condense_statements,
    get_account_id_from_arn,
    get_identity_name_from_arn,
    get_identity_type_from_arn,
)
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.s3_helpers import is_object_older_than_seconds

log = config.get_logger()


async def calculate_unused_policy_for_identity(
    host: str, account_id: str, identity_name: str, identity_type: Optional[str] = None
) -> Dict[str, Any]:
    """Generates and stories effective and unused policies for an identity.

    :param host: Tenant ID
    :param account_id: AWS Account ID
    :param identity_name: IAM Identity Name (Role name or User name)
    :param identity_type: "role" or "user", defaults to None
    :raises Exception: Raises an exception if there is a validation error
    :return: Returns a dictionary of effective and "repoed" policy documents.
    """
    if not identity_type:
        raise Exception("Unable to generate unused policy without identity type")
    arn = f"arn:aws:iam::{account_id}:{identity_type}/{identity_name}"

    s3_bucket = config.get_host_specific_key(
        "calculate_unused_policy_for_identity.s3.bucket",
        host,
        config.get(
            "_global_.s3_cache_bucket",
        ),
    )

    s3_key = config.get_host_specific_key(
        "calculate_unused_policy_for_identity.s3.file",
        host,
        f"calculate_unused_policy_for_identity/{arn}.json.gz",
    )

    if not await is_object_older_than_seconds(
        s3_key, bucket=s3_bucket, host=host, older_than_seconds=86400
    ):
        return await retrieve_json_data_from_redis_or_s3(
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            host=host,
        )

    identity_type_string = "RoleName" if identity_type == "role" else "UserName"
    try:
        managed_policy_details = await aio_wrapper(
            get_role_managed_policy_documents,
            {identity_type_string: identity_name},
            account_number=account_id,
            assume_role=config.get_host_specific_key("policies.role_name", host),
            region=config.region,
            retry_max_attempts=2,
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            host=host,
        )
    except Exception:
        sentry_sdk.capture_exception()
        raise

    effective_identity_permissions = await calculate_unused_policy_for_identities(
        host,
        [arn],
        managed_policy_details,
        account_id=account_id,
    )
    await store_json_results_in_redis_and_s3(
        effective_identity_permissions[arn],
        host=host,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
    )
    return effective_identity_permissions[arn]


async def generate_permission_removal_commands(
    identity: Any, new_policy_document: Dict[str, Any]
) -> Dict[str, str]:
    """Generates Python and AWS CLI commands to remove unused permissions.

    Generated commands will: 1) add new policy to identity, 2) remove all other policies from identity.

    :param identity: Dictionary of identity details
    :param new_policy_document: New policy document with all unused permissions removed
    :return: A dictionary of AWS CLI and Python commands to remove unused permissions
    """
    identity_type = await get_identity_type_from_arn(identity["arn"])

    identity_name = await get_identity_name_from_arn(identity["arn"])
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
    host: str,
    arns: List[str],
    managed_policy_details: Dict[str, Any],
    access_advisor_data: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
    account_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Generates effective and unused policies for a list of identities.

    :param host: Tenant ID
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
            s3_bucket=config.get_host_specific_key(
                "access_advisor.s3.bucket",
                host,
            ),
            s3_key=config.get_host_specific_key(
                "access_advisor.s3.file",
                host,
                "access_advisor/cache_access_advisor_{account_id}_v1.json.gz",
            ).format(account_id=account_id),
            host=host,
            max_age=86400,
        )

    minimum_age = config.get_host_specific_key(
        "aws.calculate_unused_policy_for_identities.max_unused_age", host, 90
    )
    ago = datetime.timedelta(minimum_age)
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    role_permissions_data = {}

    for arn in arns:
        if ":role/aws-service-role/" in arn:
            continue
        if ":role/aws-reserved" in arn:
            continue
        account_id = await get_account_id_from_arn(arn)
        role = await IAMRole.get(
            host,
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
            role_dict, effective_policy_unused_permissions_removed
        )

        role_permissions_data[arn] = {
            "arn": arn,
            "host": host,
            "effective_policy": effective_policy,
            "effective_policy_unused_permissions_removed": effective_policy_unused_permissions_removed,
            "individual_role_inline_policy_changes": individual_role_inline_policy_changes,
            "individual_role_managed_policy_changes": individual_role_managed_policy_changes,
            "permission_removal_commands": permission_removal_commands,
        }

    return role_permissions_data
