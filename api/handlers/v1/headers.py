from tornado.escape import xhtml_escape

from common.config import config
from common.handlers.base import BaseHandler, BaseMtlsHandler
from common.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class HeaderHandler(BaseHandler):
    async def get(self):
        """
        Show request headers for API requests. AuthZ is required.
            ---
            description: Shows all headers received by server
            responses:
                200:
                    description: Pretty-formatted list of headers.
        """

        if not self.user:
            return
        host = self.ctx.host
        log_data = {
            "user": self.user,
            "host": host,
            "function": "myheaders.get",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }
        log.debug(log_data)
        stats.count(
            "myheaders.get",
            tags={
                "user": self.user,
                "host": host,
            },
        )

        response_html = []

        for k, v in dict(self.request.headers).items():
            if k.lower() in map(
                str.lower,
                config.get("headers.sensitive_headers", []),
            ):
                continue
            response_html.append(
                f"<p><strong>{xhtml_escape(k)}</strong>: {xhtml_escape(v)}</p>"
            )

        self.write("{}".format("\n".join(response_html)))


class ApiHeaderHandler(BaseMtlsHandler):
    async def get(self):
        """
        Show request headers for API requests. No AuthZ required.
            ---
            description: Shows all headers received by server
            responses:
                200:
                    description: Pretty-formatted list of headers.
        """
        host = self.ctx.host
        log_data = {
            "function": "apimyheaders.get",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
            "user": self.user,
        }
        log.debug(log_data)
        stats.count(
            "apimyheaders.get",
            tags={
                "user": self.user,
                "host": host,
            },
        )
        response = {}
        for k, v in dict(self.request.headers).items():
            if k.lower() in map(
                str.lower,
                config.get("headers.sensitive_headers", []),
            ):
                continue
            response[k] = v

        self.write(response)
