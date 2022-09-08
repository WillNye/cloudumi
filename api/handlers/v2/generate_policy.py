from common.config import config
from common.handlers.base import BaseAPIV2Handler
from common.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent_bit"))()
log = config.get_logger()

BASE_INLINE_POLICY = {"Statement": [{"Action": [], "Effect": "Allow", "Resource": []}]}


class GeneratePolicyHandler(BaseAPIV2Handler):
    """Handler for /api/v2/generate_policy

    Generates an AWS role / resource policy given a set of CRUD permissions
    """

    allowed_methods = ["GET", "POST"]

    async def get(self):
        self.write(BASE_INLINE_POLICY)

    async def post(self):
        """
        POST /api/v2/generate_policy

        Determine which user is requesting access to which resource, and the type of access based on their
        selections in self-service
        """
        tenant = self.ctx.tenant
        self.write(BASE_INLINE_POLICY)
        tags = {
            "user": self.user,
            "tenant": tenant,
        }
        stats.count("RequestsHandler.post", tags=tags)
        log_data = {
            "function": "RequestsHandler.post",
            "user": self.user,
            "message": "Creating request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        self.write_error(501, message="Create request")
