from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseAPIV2Handler
from cloudumi_common.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()

log = config.get_logger()


class ErrorHandler(BaseAPIV2Handler):
    async def get(self):
        self.write_error(self.get_status())

    async def head(self):
        self.write_error(self.get_status())

    async def put(self):
        self.write_error(self.get_status())

    async def patch(self):
        self.write_error(self.get_status())

    async def post(self):
        self.write_error(self.get_status())

    async def delete(self):
        self.write_error(self.get_status())


class NotFoundHandler(ErrorHandler):
    def initialize(self):
        self.set_status(404)
