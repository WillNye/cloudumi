import tornado.web
import ujson as json

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.loader import WebpackLoader
from common.models import DataTableResponse, WebResponse

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
        host = self.ctx.host
        from common.celery_tasks.celery_tasks import app as celery_app

        res = celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            args=[host],
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

        host = self.ctx.host

        roles = []
        for arn in self.eligible_roles:
            role_name = arn.split("/")[-1]
            account_id = arn.split(":")[4]
            account_name = self.eligible_accounts.get(account_id, "")
            formatted_account_name = config.get_host_specific_key(
                "role_select_page.formatted_account_name",
                host,
                "{account_name}",
            ).format(account_name=account_name, account_id=account_id)
            roles.append(
                {
                    "arn": arn,
                    "account_name": formatted_account_name,
                    "account_id": account_id,
                    "role_name": f"[{role_name}](/policies/edit/{account_id}/iamrole/{role_name})",
                    "redirect_uri": f"/role/{arn}",
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
        host = self.ctx.host
        page_configuration = {
            "pageName": "Select a Role",
            "pageDescription": config.get_host_specific_key(
                "role_select_page.table_description",
                host,
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
                        "icon": "sign-in",
                        "content": "Sign-In",
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

        table_configuration = config.get_host_specific_key(
            "role_table_config.table_configuration_override",
            host,
            page_configuration,
        )

        self.write(table_configuration)


class FrontendHandler(tornado.web.StaticFileHandler):
    def validate_absolute_path(self, root, absolute_path):
        try:
            return super().validate_absolute_path(root, absolute_path)
        except tornado.web.HTTPError as exc:
            if exc.status_code == 404 and self.default_filename is not None:
                absolute_path = self.get_absolute_path(self.root, self.default_filename)
                return super().validate_absolute_path(root, absolute_path)
            raise exc
