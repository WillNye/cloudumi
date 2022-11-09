import re
from typing import Dict, List, Optional

from policyuniverse.expander_minimizer import _expand_wildcard_action

import common.lib.noq_json as json
from common.aws.iam.role.models import IAMRole
from common.aws.utils import ResourceAccountCache
from common.config import config
from common.exceptions.exceptions import InvalidRequestParameter, MustBeFte
from common.handlers.base import BaseAPIV1Handler, BaseHandler, BaseMtlsHandler
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.redis import redis_get

log = config.get_logger()


class AutocompleteHandler(BaseAPIV1Handler):
    async def get(self):
        """
        /api/v1/policyuniverse/autocomplete/?prefix=
        ---
        get:
            description: Supplies autocompleted permissions for the ace code editor.
            responses:
                200:
                    description: Returns a list of the matching permissions.
        """
        tenant = self.get_tenant_name()
        if (
            config.get_tenant_specific_key(
                "policy_editor.disallow_contractors", tenant, True
            )
            and self.contractor
        ):
            if self.user not in config.get_tenant_specific_key(
                "groups.can_bypass_contractor_restrictions",
                tenant,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        only_filter_services = False

        if (
            self.request.arguments.get("only_filter_services")
            and self.request.arguments.get("only_filter_services")[0].decode("utf-8")
            == "true"
        ):
            only_filter_services = True

        prefix = self.request.arguments.get("prefix")[0].decode("utf-8") + "*"
        results = _expand_wildcard_action(prefix)
        if only_filter_services:
            # We return known matching services in a format that the frontend expects to see them. We omit the wildcard
            # character returned by policyuniverse.
            services = sorted(list({r.split(":")[0].replace("*", "") for r in results}))
            results = [{"title": service} for service in services]
        else:
            results = [dict(permission=r) for r in results]
        self.write(json.dumps(results))
        await self.finish()


async def filter_resources(filter, resources, max=20):
    if filter:
        regexp = re.compile(r"{}".format(filter.strip()), re.IGNORECASE)
        results: List[str] = []
        for resource in resources:
            try:
                if regexp.search(str(resource.get(filter))):
                    if len(results) == max:
                        return results
                    results.append(resource)
            except re.error:
                # Regex error. Return no results
                pass
        return results
    else:
        return resources


async def handle_resource_type_ahead_request(cls):
    tenant = cls.get_tenant_name()
    try:
        search_string: str = cls.request.arguments.get("search")[0].decode("utf-8")
    except TypeError:
        cls.send_error(400, message="`search` parameter must be defined")
        return

    try:
        resource_type: str = cls.request.arguments.get("resource")[0].decode("utf-8")
    except TypeError:
        cls.send_error(400, message="`resource_type` parameter must be defined")
        return

    account_id = None
    topic_is_hash = True
    account_id_optional: Optional[List[bytes]] = cls.request.arguments.get("account_id")
    if account_id_optional:
        account_id = account_id_optional[0].decode("utf-8")

    limit: int = 10
    limit_optional: Optional[List[bytes]] = cls.request.arguments.get("limit")
    if limit_optional:
        limit = int(limit_optional[0].decode("utf-8"))

    # By default, we only return the S3 bucket name of a resource and not the full ARN
    # unless you specifically request it
    show_full_arn_for_s3_buckets: Optional[bool] = cls.request.arguments.get(
        "show_full_arn_for_s3_buckets"
    )

    role_name = bool(resource_type == "iam_role")
    if resource_type in ["iam_arn", "iam_role"]:
        filter_condition = None
        if account_id:
            filter_condition = IAMRole.accountId == account_id
        iam_roles = await IAMRole.query(
            tenant,
            filter_condition=filter_condition,
            attributes_to_get=["tenant", "accountId", "name", "arn", "resourceId"],
        )
        data = {iam_role.arn: iam_role.dict() for iam_role in iam_roles}
    else:
        if resource_type == "s3":
            topic = config.get_tenant_specific_key(
                "redis.s3_bucket_key", tenant, f"{tenant}_S3_BUCKETS"
            )
            s3_bucket = config.get_tenant_specific_key(
                "account_resource_cache.s3_combined.bucket", tenant
            )
            s3_key = config.get_tenant_specific_key(
                "account_resource_cache.s3_combined.file",
                tenant,
                "account_resource_cache/cache_s3_combined_v1.json.gz",
            )
        elif resource_type == "sqs":
            topic = config.get_tenant_specific_key(
                "redis.sqs_queues_key", tenant, f"{tenant}_SQS_QUEUES"
            )
            s3_bucket = config.get_tenant_specific_key(
                "account_resource_cache.sqs_combined.bucket", tenant
            )
            s3_key = config.get_tenant_specific_key(
                "account_resource_cache.sqs_combined.file",
                tenant,
                "account_resource_cache/cache_sqs_queues_combined_v1.json.gz",
            )
        elif resource_type == "sns":
            topic = config.get_tenant_specific_key(
                "redis.sns_topics_key", tenant, f"{tenant}_SNS_TOPICS"
            )
            s3_bucket = config.get_tenant_specific_key(
                "account_resource_cache.sns_topics_combined.bucket",
                tenant,
            )
            s3_key = config.get_tenant_specific_key(
                "account_resource_cache.sns_topics_topics_combined.file",
                tenant,
                "account_resource_cache/cache_sns_topics_combined_v1.json.gz",
            )
        elif resource_type == "account":
            topic = None
            s3_bucket = None
            s3_key = None
            topic_is_hash = False
        elif resource_type == "app":
            topic = config.get_tenant_specific_key(
                "celery.apps_to_roles.redis_key",
                tenant,
                f"{tenant}_APPS_TO_ROLES",
            )
            s3_bucket = None
            s3_key = None
            topic_is_hash = False
        else:
            cls.send_error(404, message=f"Invalid resource_type: {resource_type}")
            return

        if not topic and resource_type != "account":
            raise InvalidRequestParameter("Invalid resource_type specified")

        if topic and topic_is_hash and s3_key:
            data = await retrieve_json_data_from_redis_or_s3(
                redis_key=topic,
                redis_data_type="hash",
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                tenant=tenant,
            )
        elif topic:
            data = await redis_get(topic, tenant)

    results: List[Dict] = []

    unique_roles: List[str] = []

    if resource_type == "account":
        account_and_id_list = []
        account_ids_to_names = await get_account_id_to_name_mapping(tenant)
        for account_id, account_name in account_ids_to_names.items():
            account_and_id_list.append(f"{account_name} ({account_id})")
            account_str = f"{account_name} ({account_id})"
            if search_string.lower() in account_str.lower():
                results.append({"title": account_str, "account_id": account_id})
    elif resource_type == "app":
        results = {}
        filter_condition = None
        if account_id:
            filter_condition = IAMRole.accountId == account_id
        iam_role_arns = await IAMRole.query(
            tenant, filter_condition=filter_condition, attributes_to_get=["arn"]
        )
        all_role_arns = [role.arn for role in iam_role_arns]
        # Noq (Account: Test, Arn: arn)
        # TODO: Make this OSS compatible and configurable
        try:
            accounts = await get_account_id_to_name_mapping(tenant)
        except Exception as e:  # noqa
            accounts = {}

        app_to_role_map = {}
        if data:
            app_to_role_map = json.loads(data)
        seen: Dict = {}
        seen_roles = {}
        for app_name, roles in app_to_role_map.items():
            if len(results.keys()) > 9:
                break
            if search_string.lower() in app_name.lower():
                results[app_name] = {"name": app_name, "results": []}
                for role in roles:
                    account_id = await ResourceAccountCache.get(tenant, role)
                    account = accounts.get(account_id, "")
                    parsed_app_name = (
                        f"{app_name} on {account} ({account_id}) ({role})]"
                    )
                    if seen.get(parsed_app_name):
                        continue
                    seen[parsed_app_name] = True
                    seen_roles[role] = True
                    results[app_name]["results"].append(
                        {"title": role, "description": account}
                    )
        for role in all_role_arns:
            if len(results.keys()) > 9:
                break
            if search_string.lower() in role.lower():
                if seen_roles.get(role):
                    continue
                account_id = role.split(":")[4]
                account = accounts.get(account_id, "")
                if not results.get("Unknown App"):
                    results["Unknown App"] = {"name": "Unknown App", "results": []}
                results["Unknown App"]["results"].append(
                    {"title": role, "description": account}
                )

    else:
        if not data:
            return []
        for k, v in data.items():
            if account_id and k != account_id:
                continue
            if role_name:
                try:
                    r = k.split("role/")[1]
                except IndexError:
                    continue
                if search_string.lower() in r.lower():
                    if r not in unique_roles:
                        unique_roles.append(r)
                        results.append({"title": r})
            elif resource_type == "iam_arn":
                if k.startswith("arn:") and search_string.lower() in k.lower():
                    results.append({"title": k})
            else:
                list_of_items = json.loads(v)
                for item in list_of_items:
                    # A Hack to get S3 to show full ARN, and maintain backwards compatibility
                    # TODO: Fix this in V2 of resource specific typeahead endpoints
                    if resource_type == "s3" and show_full_arn_for_s3_buckets:
                        item = f"arn:aws:s3:::{item}"
                    if search_string.lower() in item.lower():
                        results.append({"title": item, "account_id": k})
                    if len(results) > limit:
                        break
            if len(results) > limit:
                break

    if len(results) == 0 and resource_type != "account":
        results.append({"title": f"{search_string}*", "account_id": ""})
    return results


class ApiResourceTypeAheadHandler(BaseMtlsHandler):
    async def get(self):
        tenant = self.get_tenant_name()
        if self.requester["name"] not in config.get_tenant_specific_key(
            "api_auth.valid_entities", tenant, []
        ):
            raise Exception("Call does not originate from a valid API caller")
        results = await handle_resource_type_ahead_request(self)
        self.write(json.dumps(results))


class ResourceTypeAheadHandler(BaseHandler):
    async def get(self):
        tenant = self.ctx.tenant
        if (
            config.get_tenant_specific_key(
                "policy_editor.disallow_contractors", tenant, True
            )
            and self.contractor
        ):
            if self.user not in config.get_tenant_specific_key(
                "groups.can_bypass_contractor_restrictions",
                tenant,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        results = await handle_resource_type_ahead_request(self)
        self.write(json.dumps(results))
