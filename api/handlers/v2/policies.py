import sys

import tornado.escape

import common.lib.noq_json as json
from common.aws.iam.policy.utils import validate_iam_policy
from common.aws.iam.role.utils import get_roles_as_resource
from common.aws.utils import (
    ResourceSummary,
    get_url_for_resource,
    list_tenant_resources,
)
from common.config import config
from common.exceptions.exceptions import ResourceNotFound
from common.handlers.base import BaseAPIV2Handler, BaseHandler
from common.lib.auth import get_accounts_user_can_view_resources_for
from common.lib.generic import filter_table
from common.lib.plugins import get_plugin_by_name
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
        tenant = self.ctx.tenant
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

        table_configuration = config.get_tenant_specific_key(
            "PoliciesTableConfigHandler.configuration",
            tenant,
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
        tenant = self.ctx.tenant
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        limit = arguments.get("limit", 1000)
        tags = {
            "user": self.user,
            "tenant": tenant,
        }
        stats.count("PoliciesHandler.post", tags=tags)
        log_data = {
            "function": "PoliciesHandler.post",
            "user": self.user,
            "message": "Writing policies",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)
        all_policies = await list_tenant_resources(tenant)

        viewable_accounts = await get_accounts_user_can_view_resources_for(
            self.user, self.groups, tenant
        )

        total_count = len(all_policies)
        policies = dict()
        for policy in all_policies:
            if policy.get("account_id") in viewable_accounts:
                if arn := policy.get("arn"):
                    policies[arn] = policy

        policies = await get_roles_as_resource(tenant, viewable_accounts, policies)
        policies = list(policies.values())

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
            policies = policies[0:limit]
            resource_summaries = await ResourceSummary.bulk_set(
                tenant, [p["arn"] for p in policies]
            )
            resource_summary_map = {rs.arn: rs for rs in resource_summaries}
            policies_to_write = []
            for policy in policies[0:limit]:
                resource_summary = resource_summary_map[policy.get("arn")]
                try:
                    url = await get_url_for_resource(resource_summary)
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
        tenant = self.ctx.tenant
        policy = tornado.escape.json_decode(self.request.body)
        if isinstance(policy, dict):
            policy = json.dumps(policy)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "policy": policy,
            "tenant": tenant,
        }
        findings = await validate_iam_policy(policy, log_data, tenant)
        self.write(json.dumps(findings))
        return
