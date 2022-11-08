import itertools

import tornado.web

import common.lib.noq_json as json
from common.aws.utils import ResourceAccountCache
from common.config import config
from common.handlers.base import (
    AuthenticatedStaticFileHandler,
    BaseHandler,
    StaticFileHandler,
)
from common.lib.aws.cached_resources.iam import (
    get_tra_supported_roles_by_tag,
    get_user_active_tra_roles_by_tag,
)
from common.lib.loader import WebpackLoader
from common.models import DataTableResponse, WebResponse
from common.user_request.models import IAMRequest

log = config.get_logger()


# TODO, move followings to util file
async def _filter_by_extension(bundle, extension):
    """Return only files with the given extension"""
    for chunk in bundle:
        if chunk["name"].endswith(".{0}".format(extension)):
            yield chunk


async def _get_bundle(name, extension, config):
    loader = WebpackLoader(name=name, config=config)
    bundle = loader.get_bundle(name)
    if extension:
        bundle = await _filter_by_extension(bundle, extension)
    return bundle


async def get_as_tags(name="main", extension=None, config=config, attrs=""):
    """
    Get a list of formatted <script> & <link> tags for the assets in the
    named bundle.

    :param bundle_name: The name of the bundle
    :param extension: (optional) filter by extension, eg. 'js' or 'css'
    :param config: (optional) the name of the configuration
    :return: a list of formatted tags as strings
    """

    bundle = await _get_bundle(name, extension, config)
    tags = []
    for chunk in bundle:
        if chunk["name"].endswith((".js", ".js.gz")):
            tags.append(
                ('<script type="text/javascript" src="{0}" {1}></script>').format(
                    chunk["url"], attrs
                )
            )
        elif chunk["name"].endswith((".css", ".css.gz")):
            tags.append(
                ('<link type="text/css" href="{0}" rel="stylesheet" {1}/>').format(
                    chunk["url"], attrs
                )
            )
    return tags


class EligibleRoleRefreshHandler(BaseHandler):
    async def get(self):
        tenant = self.ctx.tenant
        from common.celery_tasks.celery_tasks import app as celery_app

        res = celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            args=[tenant],
        )
        self.write(
            json.loads(
                WebResponse(
                    status="success",
                    message="Refresh task submitted",
                    data={
                        "task_id": res.id,
                    },
                ).json()
            )
        )


class EligibleRoleHandler(BaseHandler):
    async def post(self):
        """
        Post to the index endpoint. This will generate a list of roles the user is eligible to access on the console
        ---
        description: Retrieves a user's eligible roles for AWS console access.
        responses:
            200:
                description: json list of roles
        """

        tenant = self.ctx.tenant

        roles = []
        active_tra_roles = await get_user_active_tra_roles_by_tag(tenant, self.user)

        for arn in self.eligible_roles:
            role_name = arn.split("/")[-1]
            account_id = await ResourceAccountCache.get(tenant, arn)
            account_name = self.eligible_accounts.get(account_id, "")
            formatted_account_name = config.get_tenant_specific_key(
                "role_select_page.formatted_account_name",
                tenant,
                "{account_name}",
            ).format(account_name=account_name, account_id=account_id)
            row = {
                "arn": arn,
                "account_name": formatted_account_name,
                "account_id": account_id,
                "role_name": f"[{role_name}](/policies/edit/{account_id}/iamrole/{role_name})",
                "redirect_uri": f"/role/{arn}",
                "inactive_tra": False,
            }

            if arn in active_tra_roles:
                row["content"] = "Sign-In (Temporary Access)"
                row["color"] = "red"

            roles.append(row)

        # Check if the user already has a pending request
        ### TODO: Temporarily disable pending status checks because they incur a rate limit with pynamodax
        # TODO: https://noqdev.atlassian.net/browse/EN-1362, try tracking this in Redis instead
        # requests = [
        #     request
        #     for request in await IAMRequest.query(
        #         tenant,
        #         filter_condition=(IAMRequest.status == "pending")
        #         & (IAMRequest.username == self.user),
        #     )
        # ]
        # changes = itertools.chain(
        #     *[x.extended_request.changes.get("changes", []) for x in requests]
        # )
        # pending_requests = [
        #     {
        #         "principal": x.get("principal", {}).get("principal_arn"),
        #         "id": x.get("id", "").strip("0"),
        #     }
        #     for x in changes
        #     if x.get("change_type") == "tra_can_assume_role"
        # ]
        pending_requests = []
        ### TODO

        for role in await get_tra_supported_roles_by_tag(
            self.eligible_roles + active_tra_roles,
            self.groups + [self.user],
            self.ctx.tenant,
        ):
            """
            Update:
                button action (display modal)
            """
            arn = role["arn"]
            role_name = arn.split("/")[-1]
            account_id = await ResourceAccountCache.get(tenant, arn)
            account_name = self.eligible_accounts.get(account_id, "")
            formatted_account_name = config.get_tenant_specific_key(
                "role_select_page.formatted_account_name",
                tenant,
                "{account_name}",
            ).format(account_name=account_name, account_id=account_id)

            content = (
                "Request Temporary Access (pending)"
                if arn in [x["principal"] for x in pending_requests]
                else "Request Temporary Access"
            )
            on_click = {}
            on_click["action"] = (
                "redirect"
                if arn in [x["principal"] for x in pending_requests]
                else "open_modal"
            )
            on_click["type"] = (
                "temp_escalation_redirect"
                if arn in [x["principal"] for x in pending_requests]
                else "temp_escalation_modal"
            )
            policy_request_id = [
                x.get("id") for x in pending_requests if x.get("principal") == arn
            ]
            if policy_request_id:
                policy_request_uri = f"/policies/request/{policy_request_id[0]}"
            else:
                policy_request_uri = ""
            roles.append(
                {
                    "arn": arn,
                    "account_name": formatted_account_name,
                    "account_id": account_id,
                    "role_name": f"[{role_name}](/policies/edit/{account_id}/iamrole/{role_name})",
                    "inactive_tra": True,
                    "policy_request_uri": policy_request_uri,
                    "content": content,
                    "color": "red",
                    "onClick": on_click,
                }
            )

        # Default sort by account name
        roles = sorted(roles, key=lambda i: i.get("account_name", 0))
        total_count = len(roles)

        self.set_header("Content-Type", "application/json")
        res = DataTableResponse(
            totalCount=total_count, filteredCount=total_count, data=roles
        )
        self.write(res.json())
        await self.finish()


class EligibleRolePageConfigHandler(BaseHandler):
    async def get(self):
        """
        /eligible_roles_page_config
        ---
        get:
            description: Retrieve Role Page Configuration
            responses:
                200:
                    description: Returns Role Page Configuration
        """
        tenant = self.ctx.tenant
        page_configuration = {
            "pageName": "Select a Role",
            "pageDescription": config.get_tenant_specific_key(
                "role_select_page.table_description",
                tenant,
                "Select a role to login to the AWS console.",
            ),
            "refresh": {
                "enabled": True,
                "endpoint": "/api/v2/eligible_roles/refresh",
            },
            "tableConfig": {
                "expandableRows": True,
                "dataEndpoint": "/api/v2/eligible_roles",
                "sortable": False,
                "totalRows": 1000,
                "rowsPerPage": 50,
                "serverSideFiltering": False,
                "allowCsvExport": False,
                "allowJsonExport": False,
                "columns": [
                    {
                        "placeholder": "AWS Console Sign-In",
                        "key": "redirect_uri",
                        "type": "button",
                        "icon": "arrow right",
                        "content": "Sign-In",
                        "color": "blue",
                        "onClick": {"action": "redirect"},
                        "style": {"maxWidth": "300px"},
                    },
                    {
                        "placeholder": "Account Name",
                        "key": "account_name",
                        "type": "input",
                    },
                    {"placeholder": "Role Name", "key": "role_name", "type": "link"},
                    {"placeholder": "Account ID", "key": "account_id", "type": "input"},
                ],
            },
        }

        table_configuration = config.get_tenant_specific_key(
            "role_table_config.table_configuration_override",
            tenant,
            page_configuration,
        )

        self.write(table_configuration)


class FrontendHandler(AuthenticatedStaticFileHandler):
    def set_extra_headers(self, path):
        # Disable cache for index.html
        if self.request.path in ["/", "/index.html"]:
            self.set_header(
                "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
            )
            self.set_header("Expires", "0")
            self.set_header("Pragma", "no-cache")

    def validate_absolute_path(self, root, absolute_path):
        try:
            return super().validate_absolute_path(root, absolute_path)
        except tornado.web.HTTPError as exc:
            if exc.status_code == 404 and self.default_filename is not None:
                absolute_path = self.get_absolute_path(self.root, self.default_filename)
                return super().validate_absolute_path(root, absolute_path)
            raise exc

    async def get(self, path):
        if path == "/":
            path = "/index.html"
        await super().get(path)


class UnauthenticatedFileHandler(StaticFileHandler):
    def validate_absolute_path(self, root, absolute_path):
        try:
            return super().validate_absolute_path(root, absolute_path)
        except tornado.web.HTTPError as exc:
            if exc.status_code == 404 and self.default_filename is not None:
                absolute_path = self.get_absolute_path(self.root, self.default_filename)
                return super().validate_absolute_path(root, absolute_path)
            raise exc
