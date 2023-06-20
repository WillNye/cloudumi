import common.lib.noq_json as json
from common.config import config
from common.handlers.base import BaseMtlsHandler
from common.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class GetRolesHandler(BaseMtlsHandler):
    """CLI role handler. Pass ?all=true to URL query to return all roles."""

    def check_xsrf_cookie(self):
        pass

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        """
        /api/v1/get_roles - Endpoint used to get list of roles. Used by noq cli.
        ---
        get:
            description: Presents json-encoded list of eligible roles for the user.
            responses:
                200:
                    description: Present user with list of eligible roles.
                403:
                    description: User has failed authn/authz.
        """
        self.user: str = self.requester["email"]
        tenant = self.ctx.tenant

        include_all_roles = self.get_arguments("all")
        console_only = True
        if include_all_roles == ["true"]:
            console_only = False

        if not self.eligible_roles:
            await self.extend_eligible_roles(console_only)

        log_data = {
            "function": "GetRolesHandler.get",
            "user": self.user,
            "tenant": tenant,
            "console_only": console_only,
            "message": "Writing all eligible user roles",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        stats.count(
            "GetRolesHandler.get",
            tags={
                "user": self.user,
                "tenant": tenant,
            },
        )

        await self.authorization_flow(user=self.user, console_only=console_only)
        if not self.eligible_roles:
            await self.extend_eligible_roles(console_only=console_only)

        self.write(json.dumps(sorted(self.eligible_roles)))
        self.set_header("Content-Type", "application/json")
        await self.finish()
