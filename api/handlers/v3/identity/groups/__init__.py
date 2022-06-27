import common.lib.noq_json as json
from common.config import config
from common.handlers.base import BaseHandler
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.generic import filter_table
from common.lib.plugins import get_plugin_by_name
from common.lib.timeout import Timeout
from common.models import DataTableResponse
from identity.lib.groups.groups import (
    cache_identity_groups_for_tenant,
    get_identity_group_storage_keys,
)

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class IdentityGroupPageConfigHandler(BaseHandler):
    async def get(self):
        """
        /api/v3/identity_groups_page_config
        ---
        get:
            description: Retrieve Policies Page Configuration
            responses:
                200:
                    description: Returns Policies Page Configuration
        """
        tenant = self.ctx.tenant
        default_configuration = {
            "pageName": "Group Manager",
            "pageDescription": "",
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v3/identities/groups?markdown=true",
                "sortable": False,
                "totalRows": 1000,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "allowCsvExport": True,
                "allowJsonExport": True,
                "columns": [
                    {
                        "placeholder": "Request Access",
                        "key": "request_remove_link",
                        "type": "input",
                        "style": {"width": "150px"},
                    },
                    {
                        "placeholder": "Group Name",
                        "key": "name",
                        "type": "input",
                        "style": {"width": "110px"},
                    },
                    # {
                    #     "placeholder": "Members",
                    #     "key": "num_members",
                    #     "type": "input",
                    #     "style": {"width": "110px"},
                    # },
                    {
                        "placeholder": "IDP Name",
                        "key": "idp_name",
                        "type": "input",
                        "style": {"width": "90px"},
                    },
                    {
                        "placeholder": "Description",
                        "key": "description",
                        "type": "link",
                        "width": 6,
                        "style": {"whiteSpace": "normal", "wordBreak": "break-all"},
                    },
                ],
            },
        }

        table_configuration = config.get_tenant_specific_key(
            "IdentityGroupTableConfigHandler.configuration",
            tenant,
            default_configuration,
        )

        self.write(table_configuration)


class IdentityGroupsTableHandler(BaseHandler):
    """
    /api/v3/identities/groups?markdown=true
    Provides table contents for the identity groups table.
    1. Cache groups to DynamoDB/S3/Redis via Celery
        (Give user a Force Resync button?)
    2. Display in Groups table with advanced filtering
    3.
    """

    async def post(self):
        """
        POST /api/v2/identity/groups
        """
        tenant = self.ctx.tenant
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        config_keys = get_identity_group_storage_keys(tenant)
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        # TODO: Add server-side sorting
        # sort = arguments.get("sort")
        limit = arguments.get("limit", 1000)
        tags = {
            "user": self.user,
            "tenant": tenant,
        }
        stats.count("IdentityGroupsTableHandler.post", tags=tags)
        log_data = {
            "function": "IdentityGroupsTableHandler.post",
            "user": self.user,
            "message": "Writing items",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)
        # TODO: Cache if out-of-date, otherwise return cached data
        await cache_identity_groups_for_tenant(tenant)
        items_d = await retrieve_json_data_from_redis_or_s3(
            config_keys["redis_key"],
            s3_bucket=config_keys["s3_bucket"],
            s3_key=config_keys["s3_key"],
            tenant=tenant,
            default={},
        )
        items = list(items_d.values())

        total_count = len(items)

        if filters:
            try:
                with Timeout(seconds=5):
                    for filter_key, filter_value in filters.items():
                        items = await filter_table(filter_key, filter_value, items)
            except TimeoutError:
                self.write("Query took too long to run. Check your filter.")
                await self.finish()
                raise

        items_to_write = []
        for item in items[0:limit]:
            idp_name = item["idp_name"]
            group_name = item["name"]
            group_url = f"/group/{idp_name}/{group_name}"
            group_request_url = f"/group_request/{idp_name}/{group_name}"
            group_remove_url = f"/group_remove/{idp_name}/{group_name}"
            if item["attributes"]["requestable"]:
                item["request_remove_link"] = f"[Request Access]({group_request_url})"
            else:
                item["request_remove_link"] = "Not Requestable"
            if group_name in self.groups:
                item["request_remove_link"] = f"[Remove My Access]({group_remove_url})"

            # Convert request_id and role ARN to link
            item["name"] = f"[{group_name}]({group_url})"
            items_to_write.append(item)
        filtered_count = len(items_to_write)
        res = DataTableResponse(
            totalCount=total_count, filteredCount=filtered_count, data=items_to_write
        )
        self.write(res.json())


class IdentityGroupsHandler(BaseHandler):
    """
    Shows all groups associated with a given tenant
    """

    pass
