import ujson as json

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.generic import filter_table
from common.lib.plugins import get_plugin_by_name
from common.lib.timeout import Timeout
from common.models import DataTableResponse
from identity.lib.groups.groups import (
    cache_identity_requests_for_host,
    get_identity_request_storage_keys,
)

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class IdentityRequestsPageConfigHandler(BaseHandler):
    async def get(self):
        """
        /api/v3/identity_requests_page_config
        ---
        get:
            description: Retrieve Identity Requests Page Configuration
            responses:
                200:
                    description: Returns Identity Requests Page Configuration
        """
        host = self.ctx.host
        default_configuration = {
            "pageName": "Group Requests",
            "pageDescription": "",
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v3/identities/requests?markdown=true",
                "sortable": False,
                "totalRows": 1000,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "allowCsvExport": True,
                "allowJsonExport": True,
                "columns": [
                    {
                        "placeholder": "Request",
                        "key": "request",
                        "type": "input",
                        "style": {"width": "150px"},
                    },
                    {
                        "placeholder": "Request Time",
                        "key": "created_time",
                        "type": "daterange",
                        "style": {"width": "150px"},
                    },
                    {
                        "placeholder": "User",
                        "key": "user_field",
                        "type": "input",
                        "style": {"width": "150px"},
                    },
                    {
                        "placeholder": "Group",
                        "key": "group_field",
                        "type": "input",
                        "style": {"width": "110px"},
                    },
                    {
                        "placeholder": "Status",
                        "key": "status",
                        "type": "input",
                        "style": {"width": "90px"},
                    },
                ],
            },
        }

        table_configuration = config.get_host_specific_key(
            "IdentityRequestsPageConfigHandler.configuration",
            host,
            default_configuration,
        )

        self.write(table_configuration)


class IdentityRequestsTableHandler(BaseHandler):
    """
    /api/v3/identities/requests?markdown=true
    Provides table contents for the identity requests table.
    1. Cache requests to DynamoDB/S3/Redis via Celery
        (Give user a Force Resync button?)
    2. Display in Requests table with advanced filtering
    3.
    """

    async def post(self):
        """
        POST /api/v2/identity/requests
        """
        host = self.ctx.host
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        config_keys = get_identity_request_storage_keys(host)
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        # TODO: Add server-side sorting
        # sort = arguments.get("sort")
        limit = arguments.get("limit", 1000)
        tags = {
            "user": self.user,
            "host": host,
        }
        stats.count("IdentityRequestsTableHandler.post", tags=tags)
        log_data = {
            "function": "IdentityRequestsTableHandler.post",
            "user": self.user,
            "message": "Writing items",
            "limit": limit,
            "filters": filters,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)
        # TODO: Cache if out-of-date, otherwise return cached data
        await cache_identity_requests_for_host(host)
        items_d = await retrieve_json_data_from_redis_or_s3(
            config_keys["redis_key"],
            s3_bucket=config_keys["s3_bucket"],
            s3_key=config_keys["s3_key"],
            host=host,
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
            item["request"] = f"[View Request](/group_request/{item['request_id']})"
            item["user_field"] = ", ".join(
                [
                    f"[{u['username']}](/user/TODO_idp_name/{u['username']})"
                    for u in item["users"]
                ]
            )
            item["group_field"] = ", ".join(
                [
                    f"[{g['name']}](/user/TODO_idp_name/{g['name']})"
                    for g in item["groups"]
                ]
            )
            items_to_write.append(item)
        filtered_count = len(items_to_write)
        res = DataTableResponse(
            totalCount=total_count, filteredCount=filtered_count, data=items_to_write
        )
        self.write(res.json())
