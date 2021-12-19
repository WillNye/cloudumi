import tornado.escape
import ujson as json

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all, can_admin_identity
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.dynamo import UserDynamoHandler
from common.lib.generic import filter_table
from common.lib.plugins import get_plugin_by_name
from common.lib.timeout import Timeout
from common.lib.web import handle_generic_error_response
from common.models import DataTableResponse, WebResponse
from identity.lib.groups.models import OktaIdentityProvider
from identity.lib.groups.plugins.okta.plugin import OktaGroupManagementPlugin
from identity.lib.users.users import (
    cache_identity_users_for_host,
    get_identity_user_storage_keys,
    get_user_by_name,
)

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class IdentityUsersPageConfigHandler(BaseHandler):
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
        host = self.ctx.host
        default_configuration = {
            "pageName": "User Manager",
            "pageDescription": "",
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v3/identities/users?markdown=true",
                "sortable": False,
                "totalRows": 1000,
                "rowsPerPage": 50,
                "serverSideFiltering": True,
                "allowCsvExport": True,
                "allowJsonExport": True,
                "columns": [
                    {
                        "placeholder": "Username",
                        "key": "username",
                        "type": "input",
                        "style": {"width": "150px"},
                    },
                    {
                        "placeholder": "Status",
                        "key": "status",
                        "type": "input",
                        "style": {"width": "150px"},
                    },
                ],
            },
        }

        table_configuration = config.get_host_specific_key(
            "IdentityGroupTableConfigHandler.configuration",
            host,
            default_configuration,
        )

        self.write(table_configuration)


class IdentityUsersTableHandler(BaseHandler):
    """
    Provides table contents for the identity users table
    """

    async def post(self):
        """
        POST /api/v2/identity/users
        """
        host = self.ctx.host
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        config_keys = get_identity_user_storage_keys(host)
        arguments = json.loads(self.request.body)
        filters = arguments.get("filters")
        # TODO: Add server-side sorting
        # sort = arguments.get("sort")
        limit = arguments.get("limit", 1000)
        tags = {"user": self.user}
        stats.count("IdentityUsersTableHandler.post", tags=tags)
        log_data = {
            "function": "IdentityUsersTableHandler.post",
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
        await cache_identity_users_for_host(host)
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
            idp_name = item["idp_name"]
            user_name = item["username"]
            user_url = f"/user/{idp_name}/{user_name}"

            # Convert request_id and role ARN to link
            item["username"] = f"[{user_name}]({user_url})"
            items_to_write.append(item)
        filtered_count = len(items_to_write)
        res = DataTableResponse(
            totalCount=total_count, filteredCount=filtered_count, data=items_to_write
        )
        self.write(res.json())


class IdentityUserHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific user
    """

    async def get(self, _idp, _user_name):
        host = self.ctx.host
        log_data = {
            "function": "IdentityUserHandler.get",
            "user": self.user,
            "message": "Retrieving user information",
            "idp_name": _idp,
            "user_name": _user_name,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)
        # TODO: Authz check? this is a read only endpoint but some companies might not want all employees seeing users
        user = await get_user_by_name(host, _idp, _user_name)
        if not user:
            raise Exception("User not found")
        headers = [
            {"key": "Identity Provider Name", "value": user.idp_name},
            {
                "key": "User Name",
                "value": user.username,
            },
        ]

        self.write(
            {
                "headers": headers,
                "user": json.loads(user.json()),
                "can_admin_groups": can_admin_identity(self.user, self.groups, host),
            }
        )

    async def post(self, _idp, _user_name):
        host = self.ctx.host
        from common.celery_tasks.celery_tasks import app as celery_app

        log_data = {
            "function": "IdentityUserHandler.post",
            "user": self.user,
            "message": "Updating user",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "idp": _idp,
            "user_name": _user_name,
            "host": host,
        }
        # Checks authz levels of current user
        generic_error_message = "Unable to update user"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)

        idp_d = config.get_host_specific_key(
            "identity.identity_providers", host, default={}
        ).get(_idp)
        if not idp_d:
            raise Exception("Invalid IDP specified")
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(host, idp)
        else:
            raise Exception("IDP type is not supported.")
        user = await idp_plugin.get_user(_user_name)

        # TODO: Can Pydantic handle this piece for us?
        for k in [
            "approval_chain",
            "self_approval_users",
            "emails_to_notify_on_new_members",
        ]:
            data[k] = data[k].split(",")

        # user.attributes = UserAttributes.parse_obj(data)

        ddb = UserDynamoHandler(host)
        ddb.identity_users_table.put_item(Item=ddb._data_to_dynamo_replace(user.dict()))

        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully updated user.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_identity_users_for_host_t",
            kwargs={"host": host},
        )
        return
