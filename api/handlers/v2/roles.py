import base64
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import sentry_sdk
import tornado.escape
from furl import furl
from pydantic import ValidationError

import common.lib.noq_json as json
from common.aws.iam.role.models import IAMRole
from common.aws.iam.role.utils import update_role_access_config, update_role_tra_config
from common.config import config
from common.handlers.base import BaseAdminHandler, BaseAPIV2Handler, BaseMtlsHandler
from common.lib.auth import (
    can_create_roles,
    can_delete_iam_principals,
    can_delete_iam_principals_app,
    get_accounts_user_can_view_resources_for,
)
from common.lib.aws.cached_resources.iam import get_tra_supported_roles_by_tag
from common.lib.aws.utils import allowed_to_sync_role
from common.lib.generic import str2bool
from common.lib.plugins import get_plugin_by_name
from common.lib.v2.aws_principals import get_eligible_role_details, get_role_details
from common.models import (
    CloneRoleRequestModel,
    PrincipalModelRoleAccessConfig,
    PrincipalModelTraConfig,
    RoleCreationRequestModel,
    Status2,
    WebResponse,
)

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class RoleConsoleLoginHandler(BaseAPIV2Handler):
    async def get(self, role=None):
        """
        Attempt to retrieve credentials and redirect the user to the AWS Console
        ---
        description: Retrieves credentials and redirects user to AWS console.
        responses:
            302:
                description: Redirects to AWS console
        """
        tenant = self.ctx.tenant
        arguments = {k: self.get_argument(k) for k in self.request.arguments}
        role = role.lower()
        group_mapping = get_plugin_by_name(
            config.get_tenant_specific_key(
                "plugins.group_mapping",
                tenant,
                "cmsaas_group_mapping",
            )
        )()
        selected_roles = await group_mapping.filter_eligible_roles(role, self)
        region = arguments.get(
            "r",
            config.get_tenant_specific_key("aws.region", tenant, config.region),
        )
        redirect = arguments.get("redirect")
        read_only = arguments.get("read_only", False)
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "role": role,
            "region": region,
            "redirect": redirect,
            "ip": self.ip,
            "tenant": tenant,
        }

        log_data["role"] = role
        if not selected_roles:
            # Not authorized
            stats.count(
                "RoleConsoleLoginHandler.post",
                tags={
                    "user": self.user,
                    "role": role,
                    "authorized": False,
                    "redirect": bool(redirect),
                    "tenant": tenant,
                },
            )
            log_data[
                "message"
            ] = "You do not have any roles matching your search criteria. "
            log.debug(log_data)
            self.set_status(404)
            self.write({"type": "error", "message": log_data["message"]})
            return

        stats.count(
            "RoleConsoleLoginHandler.post",
            tags={
                "user": self.user,
                "role": role,
                "authorized": True,
                "redirect": bool(redirect),
                "tenant": tenant,
            },
        )

        if len(selected_roles) > 1:
            # Not sure which role the user wants. Redirect them to main page to select one.
            stats.count(
                "RoleConsoleLoginHandler.post",
                tags={
                    "user": self.user,
                    "role": role,
                    "authorized": False,
                    "redirect": bool(redirect),
                    "tenant": tenant,
                },
            )
            log_data[
                "message"
            ] = "You have more than one role matching your query. Please select one."
            log.debug(log_data)
            warning_message_arg = {
                "warningMessage": base64.b64encode(log_data["message"].encode()).decode(
                    "utf-8"
                )
            }
            redirect_url = furl(f"/?arn={role}")
            redirect_url.args = {
                **redirect_url.args,
                **arguments,
                **warning_message_arg,
            }
            self.write(
                {
                    "type": "redirect",
                    "message": log_data["message"],
                    "reason": "multiple_roles",
                    "redirect_url": redirect_url.url,
                }
            )
            return

        log_data["message"] = "Incoming request"
        log.debug(log_data)

        # User is authorized
        try:
            # User-role logic:
            # User-role should come in as cm-[username or truncated username]_[N or NC]
            user_role = False
            account_id = None

            selected_role = selected_roles[0]

            # User role must be defined as a user attribute
            if (
                self.user_role_name
                and "role/" in selected_role
                and selected_role.split("role/")[1] == self.user_role_name
            ):
                user_role = True
                account_id = selected_role.split("arn:aws:iam::")[1].split(":role")[0]
            aws = get_plugin_by_name(
                config.get_tenant_specific_key("plugins.aws", tenant, "cmsaas_aws")
            )()
            url = await aws.generate_url(
                self.user,
                selected_role,
                tenant,
                region=region,
                user_role=user_role,
                account_id=account_id,
                read_only=read_only,
                requester_ip=self.get_request_ip(),
            )
        except Exception as e:
            log_data["message"] = f"Exception generating AWS console URL: {str(e)}"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            stats.count(
                "index.post.exception", tags={"tenant": tenant, "error": str(e)}
            )
            self.write(
                {
                    "type": "console_url",
                    "message": tornado.escape.xhtml_escape(log_data["message"]),
                    "error": tornado.escape.xhtml_escape(str(log_data["error"])),
                }
            )
            return
        if redirect:
            parsed_url = urlparse(url)
            parsed_url_query = parse_qs(parsed_url.query)
            parsed_url_query["Destination"] = redirect
            updated_query = urlencode(parsed_url_query, doseq=True)
            url = parsed_url._replace(query=updated_query).geturl()
        self.write(
            {
                "type": "redirect",
                "redirect_url": url,
                "reason": "console_login",
                "role": selected_role,
            }
        )
        return


class RolesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles

    GET - Allows read access to a list of roles across all accounts. Returned roles are
    limited to what the requesting user has access to.
    POST - Allows (authorized) users to create a role
    """

    allowed_methods = ["GET", "POST"]

    def on_finish(self) -> None:
        if self.request.method != "POST":
            return
        from common.celery_tasks.celery_tasks import app as celery_app

        tenant = self.ctx.tenant
        # Force refresh of crednetial authorization mapping after the dynamic config sync period to ensure all workers
        # have the updated configuration
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_policies_table_details",
            kwargs={"tenant": tenant},
        )
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            kwargs={"tenant": tenant},
        )

    async def get(self):
        payload = {
            "eligible_roles": self.eligible_roles,
            "escalated_roles": await get_tra_supported_roles_by_tag(
                self.eligible_roles, self.groups, self.ctx.tenant
            ),
        }
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(payload))
        await self.finish()

    async def post(self):
        tenant = self.ctx.tenant
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "tenant": tenant,
        }
        can_create_role = can_create_roles(self.user, self.groups, tenant)
        if not can_create_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "user": self.user,
                    "authorized": can_create_role,
                    "tenant": tenant,
                },
            )
            log_data["message"] = "User is unauthorized to create a role"
            log.error(log_data)
            self.write_error(403, message="User is unauthorized to create a role")
            return

        try:
            create_model = RoleCreationRequestModel.parse_raw(self.request.body)
        except ValidationError as e:
            log_data["message"] = f"Validation Exception: {str(e)}"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(400, message="Error validating input: " + str(e))
            return

        try:
            _, results = await IAMRole.legacy_create(tenant, self.user, create_model)
        except Exception as e:
            log_data["message"] = f"Exception creating role: {str(e)}"
            log_data["error"] = str(e)
            log_data["account_id"] = create_model.account_id
            log_data["role_name"] = create_model.role_name
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "account_id": create_model.account_id,
                    "role_name": create_model.role_name,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(500, message="Exception occurred cloning role: " + str(e))
            return

        # if here, role has been successfully cloned
        stats.count(
            f"{log_data['function']}.success",
            tags={
                "user": self.user,
                "account_id": create_model.account_id,
                "role_name": create_model.role_name,
                "tenant": tenant,
            },
        )
        self.write(results)


class AccountRolesHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles/{account_number}

    Allows read access to a list of roles by account. Roles are limited to what the
    requesting user has access to.
    """

    allowed_methods = ["GET"]

    async def get(self, account_id):
        """
        GET /api/v2/roles/{account_id}
        """
        log_data = {
            "function": "AccountRolesHandler.get",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Get roles by account")


class RoleDetailHandler(BaseAPIV2Handler):
    """Handler for /api/v2/roles/{accountNumber}/{roleName}

    Allows read and update access to a specific role in an account.
    """

    allowed_methods = ["GET", "PUT", "DELETE"]

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self, account_id, role_name):
        """
        GET /api/v2/roles/{account_number}/{role_name}
        """
        tenant = self.ctx.tenant
        log_data = {
            "function": "RoleDetailHandler.get",
            "user": self.user,
            "ip": self.ip,
            "message": "Retrieving role details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
        }
        stats.count(
            "RoleDetailHandler.get",
            tags={
                "user": self.user,
                "account_id": account_id,
                "role_name": role_name,
                "tenant": tenant,
            },
        )
        log.debug(log_data)
        force_refresh = str2bool(
            self.request.arguments.get("force_refresh", [False])[0]
        )

        error = ""

        try:
            allowed_accounts_for_viewing_resources = (
                await get_accounts_user_can_view_resources_for(
                    self.user, self.groups, tenant
                )
            )
            if account_id not in allowed_accounts_for_viewing_resources:
                raise Exception(
                    f"User is not authorized to view resources for account {account_id}"
                )
            role_details = await get_role_details(
                account_id,
                role_name,
                tenant,
                extended=True,
                force_refresh=force_refresh,
                is_admin_request=self.is_admin,
            )
        except Exception as e:
            if config.get("_global_.development"):
                raise
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            role_details = None
            error = str(e)

        if role_details:
            if not allowed_to_sync_role(role_details.arn, role_details.tags, tenant):
                role_details = None

        if not role_details:
            self.send_error(
                404,
                message=f"Unable to retrieve the specified role: {account_id}/{role_name}. {error}",
            )
            return
        self.write(role_details.json())

    async def put(self, account_id, role_name):
        """
        PUT /api/v2/roles/{account_number}/{role_name}
        """
        log_data = {
            "function": "RoleDetailHandler.put",
            "user": self.user,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Update role details")

    async def delete(self, account_id, role_name):
        """
        DELETE /api/v2/roles/{account_id}/{role_name}
        """
        if not self.user:
            self.write_error(403, message="No user detected")
            return

        tenant = self.ctx.tenant

        account_id = tornado.escape.xhtml_escape(account_id)
        role_name = tornado.escape.xhtml_escape(role_name)

        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "account": account_id,
            "role": role_name,
        }
        allowed_accounts_for_viewing_resources = (
            await get_accounts_user_can_view_resources_for(
                self.user, self.groups, tenant
            )
        )
        can_delete_role = can_delete_iam_principals(self.user, self.groups, tenant)
        if (
            account_id not in allowed_accounts_for_viewing_resources
            or not can_delete_role
        ):
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "user": self.user,
                    "account": account_id,
                    "role": role_name,
                    "authorized": can_delete_role,
                    "ip": self.ip,
                    "tenant": tenant,
                },
            )
            log_data["message"] = "User is unauthorized to delete a role"
            log.error(log_data)
            self.write_error(403, message="User is unauthorized to delete a role")
            return
        try:
            await IAMRole.delete_role(tenant, account_id, role_name, self.user)
        except Exception as e:
            log_data["message"] = "Exception deleting role"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "account": account_id,
                    "role": role_name,
                    "authorized": can_delete_role,
                    "ip": self.ip,
                    "tenant": tenant,
                },
            )
            self.write_error(500, message="Error occurred deleting role: " + str(e))
            return

        # if here, role has been successfully deleted
        arn = f"arn:aws:iam::{account_id}:role/{role_name}"

        await IAMRole.get(tenant, account_id, arn, force_refresh=True)
        response_json = {
            "status": "success",
            "message": "Successfully deleted role from account",
            "role": role_name,
            "account": account_id,
        }
        self.write(response_json)


class RoleDetailAppHandler(BaseMtlsHandler):

    """Handler for /api/v2/mtls/roles/{accountNumber}/{roleName}

    Allows apps to view or delete a role
    """

    allowed_methods = ["DELETE", "GET"]

    def check_xsrf_cookie(self):
        pass

    async def delete(self, account_id, role_name):
        """
        DELETE /api/v2/mtls/roles/{account_id}/{role_name}
        """
        tenant = self.ctx.tenant
        account_id = tornado.escape.xhtml_escape(account_id)
        role_name = tornado.escape.xhtml_escape(role_name)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
            "tenant": tenant,
        }
        requester_type = self.requester.get("type")
        if requester_type != "application":
            log_data[
                "message"
            ] = "Non-application trying to access application only endpoint"
            log.error(log_data)
            self.write_error(406, message="Endpoint not supported for non-applications")
            return

        app_name = self.requester.get("name")
        allowed_accounts_for_viewing_resources = (
            await get_accounts_user_can_view_resources_for(
                self.user, self.groups, tenant
            )
        )
        can_delete_role = can_delete_iam_principals_app(app_name, tenant)

        if (
            account_id not in allowed_accounts_for_viewing_resources
            or not can_delete_role
        ):
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "app_name": app_name,
                    "account_id": account_id,
                    "role_name": role_name,
                    "authorized": can_delete_role,
                    "tenant": tenant,
                },
            )
            log_data["message"] = "App is unauthorized to delete a role"
            log.error(log_data)
            self.write_error(403, message="App is unauthorized to delete a role")
            return

        try:
            await IAMRole.delete_role(tenant, account_id, role_name, app_name)
        except Exception as e:
            log_data["message"] = "Exception deleting role"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "app_name": app_name,
                    "account_id": account_id,
                    "role_name": role_name,
                    "authorized": can_delete_role,
                    "tenant": tenant,
                },
            )
            self.write_error(500, message="Error occurred deleting role: " + str(e))
            return

        # if here, role has been successfully deleted
        arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        await IAMRole.get(tenant, account_id, arn, force_refresh=True)
        response_json = {
            "status": "success",
            "message": "Successfully deleted role from account",
            "role": role_name,
            "account": account_id,
        }
        self.write(response_json)

    async def get(self, account_id, role_name):
        """
        GET /api/v2/mtls/roles/{account_id}/{role_name}
        """
        tenant = self.ctx.tenant
        account_id = tornado.escape.xhtml_escape(account_id)
        role_name = tornado.escape.xhtml_escape(role_name)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "ip": self.ip,
            "message": "Retrieving role details",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "role_name": role_name,
        }
        app_name = self.requester.get("name") or self.requester.get("username")
        stats.count(
            "RoleDetailAppHandler.get",
            tags={
                "requester": app_name,
                "account_id": account_id,
                "role_name": role_name,
                "tenant": tenant,
            },
        )
        log.debug(log_data)
        force_refresh = str2bool(
            self.request.arguments.get("force_refresh", [False])[0]
        )

        error = ""

        try:
            allowed_accounts_for_viewing_resources = (
                await get_accounts_user_can_view_resources_for(
                    self.user, self.groups, tenant
                )
            )
            if account_id not in allowed_accounts_for_viewing_resources:
                raise Exception("User is not authorized to view this resource")
            role_details = await get_role_details(
                account_id,
                role_name,
                tenant,
                extended=True,
                force_refresh=force_refresh,
            )
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            role_details = None
            error = str(e)

        if not role_details:
            self.send_error(
                404,
                message=f"Unable to retrieve the specified role: {account_id}/{role_name}. {error}",
            )
            return
        self.write(role_details.json())


class RoleCloneHandler(BaseAPIV2Handler):
    """Handler for /api/v2/clone/role

    Allows cloning a role.
    """

    allowed_methods = ["POST"]

    async def post(self):
        tenant = self.ctx.tenant
        log_data = {
            "user": self.user,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "tenant": tenant,
        }

        can_create_role = can_create_roles(self.user, self.groups, tenant)
        if not can_create_role:
            stats.count(
                f"{log_data['function']}.unauthorized",
                tags={
                    "user": self.user,
                    "authorized": can_create_role,
                    "tenant": tenant,
                },
            )
            log_data["message"] = "User is unauthorized to clone a role"
            log.error(log_data)
            self.write_error(403, message="User is unauthorized to clone a role")
            return

        try:
            clone_model = CloneRoleRequestModel.parse_raw(self.request.body)
        except ValidationError as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(400, message="Error validating input: " + str(e))
            return

        try:
            _, results = await IAMRole.clone(tenant, self.user, clone_model)
        except Exception as e:
            log_data["message"] = "Exception cloning role"
            log_data["error"] = str(e)
            log_data["account_id"] = clone_model.account_id
            log_data["role_name"] = clone_model.role_name
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.exception",
                tags={
                    "user": self.user,
                    "account_id": clone_model.account_id,
                    "role_name": clone_model.role_name,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(500, message="Exception occurred cloning role: " + str(e))
            return

        # if here, role has been successfully cloned
        self.write(results)


class GetRolesMTLSHandler(BaseMtlsHandler):
    """
    Handler for /api/v2/get_roles
    Noq MTLS role handler - returns User's eligible roles and other details about eligible roles
    Pass ?all=true to URL query to return all roles.
    """

    def check_xsrf_cookie(self):
        pass

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        """
        GET /api/v2/get_roles - Endpoint used to get details of eligible roles. Used by noq.
        ---
        get:
            description: Returns a json-encoded list of objects of eligible roles for the user.
            response format: WebResponse. The "data" field within WebResponse is of format EligibleRolesModelArray
            Example response:
                {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "roles": [
                                    {
                                        "arn": "arn:aws:iam::123456789012:role/role_name",
                                        "account_id": "123456789012",
                                        "account_friendly_name": "prod",
                                        "role_name": "role_name",
                                        "apps": {
                                            "app_details": [
                                                {
                                                    "name": "noq",
                                                    "owner": "owner@example.com",
                                                    "owner_url": null,
                                                    "app_url": "https://example.com"
                                                }
                                            ]
                                        }
                                    },
                                    ...
                                ]
                    }
                }
        """
        tenant = self.ctx.tenant
        self.user: str = self.requester["email"]

        include_all_roles = self.get_arguments("all")
        console_only = True
        if include_all_roles == ["true"]:
            console_only = False

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "console_only": console_only,
            "message": "Getting all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)
        stats.count(
            "GetRolesMTLSHandler.get",
            tags={
                "user": self.user,
                "tenant": tenant,
            },
        )

        await self.authorization_flow(user=self.user, console_only=console_only)
        eligible_roles_details_array = await get_eligible_role_details(
            sorted(self.eligible_roles),
            tenant,
        )

        res = WebResponse(
            status=Status2.success,
            status_code=200,
            data=eligible_roles_details_array.dict(),
        )
        self.write(res.json(exclude_unset=True))
        await self.finish()


class RoleTraConfigHandler(BaseAdminHandler):
    """Handler for /api/v2/roles/{accountNumber}/{roleName}/elevated-access-config

    Allows an admin to update access to a specific role in an account.
    """

    allowed_methods = ["PUT"]

    async def put(self, account_id, role_name):
        """
        PUT /api/v2/roles/{account_number}/{role_name}/elevated-access-config
        """
        tenant = self.ctx.tenant
        log_data = {
            "function": "RoleDetailHandler.put",
            "user": self.user,
            "message": "Updating Role TRA Config",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "tenant": tenant,
            "role_name": role_name,
        }
        log.debug(log_data)

        try:
            tra_config = PrincipalModelTraConfig.parse_raw(self.request.body)
        except ValidationError as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(400, message="Error validating input: " + str(e))
            return

        update_successful, err = await update_role_tra_config(
            tenant, self.user, role_name, account_id, tra_config
        )
        if not update_successful:
            self.set_status(500, err)
            return

        try:
            role_details = await get_role_details(
                account_id,
                role_name,
                tenant,
                extended=True,
                force_refresh=True,
                is_admin_request=self.is_admin,
            )
            self.write(role_details.json())
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            self.set_status(
                500,
                f"Update successful but error encountered when retrieving role: {str(e)}",
            )


class RoleAccessConfigHandler(BaseAdminHandler):
    """Handler for /api/v2/roles/{accountNumber}/{roleName}/access

    Allows an admin to update access to a specific role in an account.
    """

    allowed_methods = ["PUT"]

    async def put(self, account_id, role_name):
        """
        PUT /api/v2/roles/{account_number}/{role_name}/access
        """
        tenant = self.ctx.tenant
        log_data = {
            "function": "RoleAccessConfigHandler.put",
            "user": self.user,
            "message": "Updating Role access Config",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "tenant": tenant,
            "role_name": role_name,
        }
        log.debug(log_data)

        try:
            role_access_config = PrincipalModelRoleAccessConfig.parse_raw(
                self.request.body
            )
        except ValidationError as e:
            log_data["message"] = "Validation Exception"
            log.error(log_data, exc_info=True)
            stats.count(
                f"{log_data['function']}.validation_exception",
                tags={
                    "user": self.user,
                    "tenant": tenant,
                },
            )
            sentry_sdk.capture_exception()
            self.write_error(400, message="Error validating input: " + str(e))
            return

        update_successful, err = await update_role_access_config(
            tenant, self.user, role_name, account_id, role_access_config
        )
        if not update_successful:
            self.set_status(500, err)
            return

        try:
            role_details = await get_role_details(
                account_id,
                role_name,
                tenant,
                extended=True,
                force_refresh=True,
                is_admin_request=self.is_admin,
            )
            self.write(role_details.json())
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            self.set_status(
                500,
                f"Update successful but error encountered when retrieving role: {str(e)}",
            )
