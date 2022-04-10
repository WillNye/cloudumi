import sys

import tornado.escape
import ujson as json

from common.config import config
from common.exceptions.exceptions import ResourceNotFound
from common.handlers.base import BaseAPIV2Handler, BaseHandler
from common.lib.auth import get_accounts_user_can_view_resources_for
from common.lib.aws.utils import validate_iam_policy
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.generic import filter_table
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import get_url_for_resource
from common.lib.timeout import Timeout
from common.models import DataTableResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class PoliciesPageConfigHandler(BaseHandler):
    async def get(self):
        """
        /api/v2/policies_page_config
        ---
        get:
            description: Retrieve Policies Page Configuration
            responses:
                200:
                    description: Returns Policies Page Configuration
        """
        host = self.ctx.host
        default_configuration = {
            "pageName": "All Resources",
            "pageDescription": "View all of the resources we know about.",
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v2/policies?markdown=true",
                "sortable": False,
                "totalRows": 1000,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "allowCsvExport": True,
                "allowJsonExport": True,
                "columns": [
                    {
                        "placeholder": "Account ID",
                        "key": "account_id",
                        "type": "input",
                        "style": {"width": "110px"},
                    },
                    {
                        "placeholder": "Account",
                        "key": "account_name",
                        "type": "input",
                        "style": {"width": "90px"},
                    },
                    {
                        "placeholder": "Resource",
                        "key": "arn",
                        "type": "link",
                        "width": 6,
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                    },
                    {
                        "placeholder": "Tech",
                        "key": "technology",
                        "type": "input",
                        "style": {"width": "70px"},
                    },
                ],
            },
        }

        table_configuration = config.get_host_specific_key(
            "PoliciesTableConfigHandler.configuration",
            host,
            default_configuration,
        )

        self.write(table_configuration)


class PoliciesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/policies

    Api endpoint to list and filter policy requests.
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v2/policies
        """
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        markdown = arguments.get("markdown")
        host = self.ctx.host
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        limit = arguments.get("limit", 1000)
        tags = {"user": self.user}
        stats.count("PoliciesHandler.post", tags=tags)
        log_data = {
            "function": "PoliciesHandler.post",
            "user": self.user,
            "message": "Writing policies",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)
        all_policies = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get_host_specific_key(
                "policies.redis_policies_key",
                host,
                f"{host}_ALL_POLICIES",
            ),
            s3_bucket=config.get_host_specific_key(
                "cache_policies_table_details.s3.bucket", host
            ),
            s3_key=config.get_host_specific_key(
                "cache_policies_table_details.s3.file",
                host,
                "policies_table/cache_policies_table_details_v1.json.gz",
            ),
            default=[],
            host=host,
        )

        allowed_accounts_for_viewing_resources = (
            await get_accounts_user_can_view_resources_for(self.user, self.groups, host)
        )

        total_count = len(all_policies)
        policies = []
        for policy in all_policies:
            if not policy.get("account_id") in allowed_accounts_for_viewing_resources:
                continue
            policies.append(policy)

        if filters:
            try:
                with Timeout(seconds=5):
                    for filter_key, filter_value in filters.items():
                        policies = await filter_table(
                            filter_key, filter_value, policies
                        )
            except TimeoutError:
                self.write("Query took too long to run. Check your filter.")
                await self.finish()
                raise

        if markdown:
            policies_to_write = []
            for policy in policies[0:limit]:
                resource_name = policy.get("arn").split(":")[5]
                if "/" in resource_name:
                    resource_name = resource_name.split("/")[-1]
                region = policy["arn"].split(":")[3]
                try:
                    url = await get_url_for_resource(
                        policy["arn"],
                        host,
                        policy["technology"],
                        policy["account_id"],
                        region,
                        resource_name,
                    )
                except ResourceNotFound:
                    url = ""
                if url:
                    policy["arn"] = f"[{policy['arn']}]({url})"
                if not policy.get("templated"):
                    policy["templated"] = "N/A"
                else:
                    if "/" in policy["templated"]:
                        link_name = policy["templated"].split("/")[-1]
                        policy["templated"] = f"[{link_name}]({policy['templated']})"
                policies_to_write.append(policy)
        else:
            policies_to_write = policies[0:limit]
        filtered_count = len(policies_to_write)
        res = DataTableResponse(
            totalCount=total_count, filteredCount=filtered_count, data=policies_to_write
        )
        self.write(res.json())
        return


class CheckPoliciesHandler(BaseAPIV2Handler):
    async def post(self):
        """
        POST /api/v2/policies/check
        """
        host = self.ctx.host
        policy = tornado.escape.json_decode(self.request.body)
        if isinstance(policy, dict):
            policy = json.dumps(policy)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy": policy,
            "host": host,
        }
        findings = await validate_iam_policy(policy, log_data, host)
        self.write(json.dumps(findings))
        return
