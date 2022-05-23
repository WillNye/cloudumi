from datetime import datetime, timedelta
from typing import List, Optional, Union

import ujson as json
from policy_sentry.util.arns import parse_arn

from common.aws.iam.utils import fetch_iam_role, fetch_iam_user
from common.config import config
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.asyncio import aio_wrapper
from common.lib.aws.iam import get_active_tear_users_tag, get_tear_support_groups_tag
from common.lib.aws.utils import get_role_tag
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import get_aws_config_history_url_for_resource
from common.lib.redis import RedisHandler, redis_get
from common.models import (
    AppDetailsArray,
    AwsPrincipalModel,
    CloudTrailDetailsModel,
    CloudTrailErrorArray,
    EligibleRolesModel,
    EligibleRolesModelArray,
    ExtendedAwsPrincipalModel,
    PrincipalModelTearConfig,
    S3DetailsModel,
    S3Error,
    S3ErrorArray,
)

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


async def get_config_timeline_url_for_role(role, account_id, host):
    resource_id = role.get("resourceId")
    if resource_id:
        config_history_url = await get_aws_config_history_url_for_resource(
            account_id, resource_id, role["arn"], "AWS::IAM::Role", host
        )
        return config_history_url


async def get_cloudtrail_details_for_role(arn: str, host: str):
    """
    Retrieves CT details associated with role, if they exist exists
    :param arn:
    :return:
    """
    # internal_policies = get_plugin_by_name(
    #     config.get_host_specific_key(
    #         "plugins.internal_policies", host, "cmsaas_policies"
    #     )
    # )()
    # error_url = config.get_host_specific_key(
    #     "cloudtrail_errors.error_messages_by_role_uri", host, ""
    # ).format(arn=arn)
    #
    # errors_unformatted = await internal_policies.get_errors_by_role(
    #     arn,
    #     host,
    #     config.get_host_specific_key(
    #         "policies.number_cloudtrail_errors_to_display", host, 5
    #     ),
    # )
    #
    # ct_errors = []
    #
    # for event_string, value in errors_unformatted.items():
    #     event_call, resource = event_string.split("|||")
    #     ct_errors.append(
    #         CloudTrailError(
    #             event_call=event_call,
    #             resource=resource,
    #             generated_policy=value.get("generated_policy"),
    #             count=value.get("count", 0),
    #         )
    #     )
    #
    # return CloudTrailDetailsModel(
    #     error_url=error_url, errors=CloudTrailErrorArray(cloudtrail_errors=ct_errors)
    # )
    return CloudTrailDetailsModel(
        error_url="", errors=CloudTrailErrorArray(cloudtrail_errors=[])
    )


async def get_s3_details_for_role(
    account_id: str, role_name: str, host: str
) -> S3DetailsModel:
    """
    Retrieves s3 details associated with role, if it exists
    :return:
    """
    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
    error_url = config.get_host_specific_key("s3.query_url", host, "").format(
        yesterday=yesterday, role_name=f"'{role_name}'", account_id=f"'{account_id}'"
    )
    query_url = config.get_host_specific_key("s3.non_error_query_url", host, "").format(
        yesterday=yesterday, role_name=f"'{role_name}'", account_id=f"'{account_id}'"
    )

    s3_error_topic = config.get_host_specific_key(
        "redis.s3_errors", host, f"{host}_S3_ERRORS"
    )
    all_s3_errors = await redis_get(s3_error_topic, host)
    s3_errors_unformatted = []
    if all_s3_errors:
        s3_errors_unformatted = json.loads(all_s3_errors).get(arn, [])
    s3_errors_formatted = []
    for error in s3_errors_unformatted:
        s3_errors_formatted.append(
            S3Error(
                count=error.get("count", ""),
                bucket_name=error.get("bucket_name", ""),
                request_prefix=error.get("request_prefix", ""),
                error_call=error.get("error_call", ""),
                status_code=error.get("status_code", ""),
                status_text=error.get("status_text", ""),
                role_arn=arn,
            )
        )

    return S3DetailsModel(
        query_url=query_url,
        error_url=error_url,
        errors=S3ErrorArray(s3_errors=s3_errors_formatted),
    )


async def get_app_details_for_role(arn: str, host: str):
    """
    Retrieves applications associated with role, if they exist
    :param arn:
    :return:
    """
    return AppDetailsArray(app_details=[])
    # internal_policies = get_plugin_by_name(
    #     config.get_host_specific_key(
    #         "plugins.internal_policies", host, "cmsaas_policies"
    #     )
    # )()
    # return await internal_policies.get_applications_associated_with_role(arn, host)


async def get_role_template(arn: str, host: str):
    red = RedisHandler().redis_sync(host)
    return await aio_wrapper(
        red.hget,
        config.get_host_specific_key(
            "templated_roles.redis_key",
            host,
            f"{host}_TEMPLATED_ROLES_v2",
        ),
        arn.lower(),
    )


async def get_user_details(
    account_id: str,
    user_name: str,
    host: str,
    extended: bool = False,
    force_refresh: bool = False,
) -> Optional[Union[ExtendedAwsPrincipalModel, AwsPrincipalModel]]:
    account_ids_to_name = await get_account_id_to_name_mapping(host)
    arn = f"arn:aws:iam::{account_id}:user/{user_name}"

    user = await fetch_iam_user(account_id, arn, host)
    # requested user doesn't exist
    if not user:
        return None
    if extended:
        return ExtendedAwsPrincipalModel(
            name=user_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
            inline_policies=user.get("UserPolicyList", []),
            config_timeline_url=await get_config_timeline_url_for_role(
                user, account_id, host
            ),
            cloudtrail_details=await get_cloudtrail_details_for_role(arn, host),
            s3_details=await get_s3_details_for_role(
                account_id=account_id,
                role_name=user_name,
                host=host,
            ),
            apps=await get_app_details_for_role(arn, host),
            managed_policies=user["AttachedManagedPolicies"],
            groups=user["Groups"],
            tags=user["Tags"],
            owner=user.get("owner"),
            templated=False,
            template_link=None,
            created_time=str(user.get("CreateDate", "")),
            last_used_time=user.get("RoleLastUsed", {}).get("LastUsedDate"),
            description=user.get("Description"),
            permissions_boundary=user.get("PermissionsBoundary", {}),
        )
    else:
        return AwsPrincipalModel(
            name=user_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
        )


async def get_role_details(
    account_id: str,
    role_name: str,
    host: str,
    extended: bool = False,
    force_refresh: bool = False,
    is_admin_request: bool = False,
) -> Optional[Union[ExtendedAwsPrincipalModel, AwsPrincipalModel]]:
    account_ids_to_name = await get_account_id_to_name_mapping(host)
    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    role = await fetch_iam_role(account_id, arn, host, force_refresh=force_refresh)
    # requested role doesn't exist
    if not role:
        return None
    if extended:
        elevated_access_config = None
        template = await get_role_template(arn, host)
        tags = role["policy"]["Tags"]
        if config.get_host_specific_key("elevated_access.enabled", host, False):
            tear_support_tag = get_tear_support_groups_tag(host)
            tear_users_tag = get_active_tear_users_tag(host)
            tear_tags = [tear_support_tag, tear_users_tag]
            if is_admin_request:
                active_users = get_role_tag(role, tear_users_tag, True, set())
                supported_groups = get_role_tag(role, tear_support_tag, True, set())

                elevated_access_config = PrincipalModelTearConfig(
                    active_users=list(active_users),
                    supported_groups=list(supported_groups),
                )

            tags = [tag for tag in tags if tag["Key"] not in tear_tags]

        return ExtendedAwsPrincipalModel(
            name=role_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
            inline_policies=role["policy"].get(
                "RolePolicyList", role["policy"].get("UserPolicyList", [])
            ),
            assume_role_policy_document=role["policy"]["AssumeRolePolicyDocument"],
            config_timeline_url=await get_config_timeline_url_for_role(
                role, account_id, host
            ),
            cloudtrail_details=await get_cloudtrail_details_for_role(arn, host),
            s3_details=await get_s3_details_for_role(
                account_id=account_id,
                role_name=role_name,
                host=host,
            ),
            apps=await get_app_details_for_role(arn, host),
            managed_policies=role["policy"]["AttachedManagedPolicies"],
            tags=tags,
            elevated_access_config=elevated_access_config,
            templated=bool(template),
            template_link=template,
            created_time=role["policy"].get("CreateDate"),
            last_used_time=role["policy"].get("RoleLastUsed", {}).get("LastUsedDate"),
            description=role["policy"].get("Description"),
            owner=role.get("owner"),
            permissions_boundary=role["policy"].get("PermissionsBoundary", {}),
        )
    else:
        return AwsPrincipalModel(
            name=role_name,
            account_id=account_id,
            account_name=account_ids_to_name.get(account_id, None),
            arn=arn,
        )


async def get_eligible_role_details(
    eligible_roles: List[str],
    host: str,
) -> EligibleRolesModelArray:
    account_ids_to_name = await get_account_id_to_name_mapping(host)
    eligible_roles_detailed = []
    for role in eligible_roles:
        arn_parsed = parse_arn(role)
        account_id = arn_parsed["account"]
        role_name = (
            arn_parsed["resource_path"]
            if arn_parsed["resource_path"]
            else arn_parsed["resource"]
        )
        account_friendly_name = account_ids_to_name.get(account_id, "Unknown")
        role_apps = await get_app_details_for_role(role, host)
        eligible_roles_detailed.append(
            EligibleRolesModel(
                arn=role,
                account_id=account_id,
                account_friendly_name=account_friendly_name,
                role_name=role_name,
                apps=role_apps,
            )
        )

    return EligibleRolesModelArray(roles=eligible_roles_detailed)
