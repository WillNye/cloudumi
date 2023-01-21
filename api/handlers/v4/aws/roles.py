# import itertools

import tornado.web

import common.lib.noq_json as json
from common.aws.utils import ResourceAccountCache
from common.config import config
from common.handlers.base import (
    AuthenticatedStaticFileHandler,
    BaseAPIV2Handler,
    BaseHandler,
    StaticFileHandler,
)
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.auth import get_accounts_user_can_view_resources_for
from common.lib.aws.cached_resources.iam import (
    get_tra_supported_roles_by_tag,
    get_user_active_tra_roles_by_tag,
)
from common.lib.filter import filter_data
from common.lib.loader import WebpackLoader
from common.lib.plugins import get_plugin_by_name
from common.models import DataTableResponse, WebResponse

# from common.user_request.models import IAMRequest

log = config.get_logger()


class RolesHandler(BaseHandler):
    """Handler for /api/v4/aws/roles

    Api endpoint to list and filter roles
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        GET /api/v4/aws/roles
        """
        tenant = self.ctx.tenant
        body = tornado.escape.json_decode(self.request.body)

        group_mapping = get_plugin_by_name(
            config.get_tenant_specific_key(
                "plugins.group_mapping",
                tenant,
                "cmsaas_group_mapping",
            )
        )()

        eligible_roles = await get_user_active_tra_roles_by_tag(tenant, self.user)
        self.eligible_roles = await group_mapping.get_eligible_roles(
            self.eligible_roles,
            self.user,
            self.groups,
            self.user_role_name,
            self.get_tenant_name(),
            console_only=True,
        )

        filtered_roles = await filter_data(eligible_roles, body)
        # page_size = body.get("pageSize", 50)
        # sorting_column = body.get("sortingColumn", "account")
        # sorting_descending = body.get("sortingDescending", False)
        # filtering_tokens = body.get("filteringTokens", [])
        # # example: [
        # #   {
        # #     propertyKey: "domainName",
        # #     operator: "!=",
        # #     value: "asdf",
        # #   },
        # # ]
        # filtering_text = body.get("filteringText", "")
        # filtering_operation = body.get("filteringOperation", "and")
        # current_page_index = body.get("currentPageIndex", 0)

        viewable_accounts = await get_accounts_user_can_view_resources_for(
            self.user, self.groups, tenant
        )

        eligible_roles = [
            [
                {
                    "arn": "arn:aws:iam::420317713496:role/noq_audit_admin",
                    "account_name": "Noq Audit",
                    "account_id": "420317713496",
                    "role_name": "[noq_audit_admin](/policies/edit/420317713496/iamrole/noq_audit_admin)",
                    "redirect_uri": "/role/arn:aws:iam::420317713496:role/noq_audit_admin",
                    "inactive_tra": False,
                }
            ]
        ]

        total_count = len(eligible_roles)
        matching_roles = dict()
        # for role in eligible_roles:
        #     full_match = True
        #     for token in filtering_tokens:
        #         # : == contains. Don't ask why
        #         token_match = True
        #         if token["operator"] == ":":
        #             if not token.get("propertyKey"):
        #                 for _, v in role.items():
        #                     if token["value"] in v:
        #                         token_match = True
        #                         break
        #             elif token["propertyKey"] not in role:
        #                 token_match = False
        #                 break
        #             elif token["value"] not in role[token["propertyKey"]]:
        #                 token_match = False
        #                 break
        #         elif token["operator"] == "!=":
        #             if token["propertyKey"] not in role:
        #                 token_match = False
        #                 break
        #             if token["value"] == role.get(token.get("propertyKey")):
        #                 token_match = False
        #                 break
        #         elif token["operator"] == "=":
        #             if token["propertyKey"] not in role:
        #                 token_match = False
        #                 break
        #             if token["value"] != role[token["propertyKey"]]:
        #                 token_match = False
        #                 break
        #         if filtering_operation == "and" and not token_match:
        #             full_match = False
        #             break
        #         if filtering_operation == "or" and token_match:
        #             full_match = True
        #             break
        #         else:
        #             raise ValueError(f"Invalid operator {token['operator']}")
        #     if match:
        #         pass

        # policies = await get_roles_as_resource(tenant, viewable_accounts, policies)
        # policies = list(policies.values())

        # if filters:
        #     try:
        #         with Timeout(seconds=5):
        #             for filter_key, filter_value in filters.items():
        #                 policies = await filter_table(
        #                     filter_key, filter_value, policies
        #                 )
        #     except TimeoutError:
        #         self.write("Query took too long to run. Check your filter.")
        #         await self.finish()
        #         raise

        # if markdown:
        #     policies = policies[0:limit]
        #     resource_summaries = await ResourceSummary.bulk_set(
        #         tenant, [p["arn"] for p in policies]
        #     )
        #     resource_summary_map = {rs.arn: rs for rs in resource_summaries}
        #     policies_to_write = []
        #     for policy in policies[0:limit]:
        #         resource_summary = resource_summary_map[policy.get("arn")]
        #         try:
        #             url = await get_url_for_resource(resource_summary)
        #         except ResourceNotFound:
        #             url = ""
        #         if url:
        #             policy["arn"] = f"[{policy['arn']}]({url})"
        #         if not policy.get("templated"):
        #             policy["templated"] = "N/A"
        #         else:
        #             if "/" in policy["templated"]:
        #                 link_name = policy["templated"].split("/")[-1]
        #                 policy["templated"] = f"[{link_name}]({policy['templated']})"
        #         policies_to_write.append(policy)
        # else:
        #     policies_to_write = policies[0:limit]
        # filtered_count = len(policies_to_write)
        # res = DataTableResponse(
        #     totalCount=total_count, filteredCount=filtered_count, data=policies_to_write
        # )
        # self.write(res.json())
        # return
