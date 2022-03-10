import datetime

import ujson as json

from common.config import config
from common.lib.aws.access_advisor import get_epoch_authenticated
from common.lib.aws.fetch_iam_principal import fetch_iam_role
from common.lib.aws.utils import calculate_policy_changes, condense_statements
from common.lib.cache import retrieve_json_data_from_redis_or_s3

log = config.get_logger()


async def calculate_unused_policy_for_identities(
    host,
    arns,
    managed_policy_details,
    aa_data=None,
    force_refresh=False,
    account_id=None,
):

    if not aa_data:
        if not account_id:
            raise Exception("Unable to retrieve access advisor data without account ID")
        aa_data = await retrieve_json_data_from_redis_or_s3(
            s3_bucket=config.get_host_specific_key(
                "cache_iam_resources_for_account.iam_policies.s3.bucket",
                host,
            ),
            s3_key=config.get_host_specific_key(
                "cache_iam_resources_for_account.iam_policies.s3.file",
                host,
                "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
            ).format(resource_type="access_advisor", account_id=account_id),
            host=host,
            max_age=86400,
        )

    # managed_policy_details = {}

    # for policy in managed_policies:
    #     policy_name = policy["PolicyName"]
    #     for policy_version in policy["PolicyVersionList"]:
    #         if policy_version["IsDefaultVersion"]:
    #             managed_policy_details[policy_name] = policy_version["Document"]
    #             break

    minimum_age = 90  # TODO: Make this configurable
    ago = datetime.timedelta(minimum_age)
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    role_permissions_data = {}

    for arn in arns:
        if ":role/aws-service-role/" in arn:
            continue
        if ":role/aws-reserved" in arn:
            continue
        account_id = arn.split(":")[4]
        role = await fetch_iam_role(
            account_id,
            arn,
            host,
            force_refresh=force_refresh,
            run_sync=True,
        )
        role_name = role["name"]

        account_number = role["accountId"]

        # Get last-used data for role
        aa_data_for_role = aa_data.get(role["arn"], [])
        used_services = set()
        unused_services = set()

        for service in aa_data_for_role:
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
            role, used_services, policy_type="inline_policy"
        )

        individual_role_managed_policy_changes = await calculate_policy_changes(
            role,
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

        role_permissions_data[arn] = {
            "arn": arn,
            "host": host,
            "effective_policy": effective_policy,
            "effective_policy_unused_permissions_removed": effective_policy_unused_permissions_removed,
            "individual_role_inline_policy_changes": individual_role_inline_policy_changes,
            "individual_role_managed_policy_changes": individual_role_managed_policy_changes,
        }

    return role_permissions_data


# Take recommended actions: Add new policy, and remove old policies
# Athena

#     athena_config = {
#         "account_id": "259868150464",
#         "region": "us-west-2",
#         "table_name": "cloudtrail_logs_noq",
#         "date_look_back": "90",
#     }
#     table_name = athena_config["table_name"]
#     date_look_back = athena_config["date_look_back"]

#     query = f"""select distinct eventsource,
# 	eventname,
# 	useridentity.sessioncontext.sessionissuer.arn,
# 	resources
# from {table_name}
# where useridentity.sessioncontext.sessionissuer.arn not like '%:role/aws-service-role/%'
# 	and date_parse(date, '%Y/%m/%d') > current_timestamp - interval '{date_look_back}' day
#     """

#     athena_client = boto3_cached_conn(
#         "athena",
#         host,
#         account_number=athena_config["account_id"],
#         assume_role=config.get_host_specific_key("policies.role_name", host),
#         region=config.region,
#         sts_client_kwargs=dict(
#             region_name=config.region,
#             endpoint_url=f"https://sts.{config.region}.amazonaws.com",
#         ),
#         client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
#         session_name=sanitize_session_name("noq_athena_cloudtrail_query"),
#     )

#     athena_client.start_query_execution()

# TODO: Figure out table name
# TODO: Calculate event time
# query = """SELECT distinct useridentity.sessioncontext.sessionissuer.arn, eventSource, eventName, eventSource FROM
# eb531e81-49f4-4eb9-bf06-93ba8de5846f WHERE eventTime >= '2021-09-16 00:00:00'
# """
#
# response = client.start_query(
#     QueryStatement='string'
# )
