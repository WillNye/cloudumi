"""Web routes."""
import sentry_sdk
import tornado.autoreload
import tornado.web
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration

from common.config import config
from cloudumi_saml.handlers.v1.saml import SamlHandler

log = config.get_logger()


def make_app(jwt_validator=None):
    """make_app."""

    routes = [
        (r"/saml/(.*)", SamlHandler),
    ]

    app = tornado.web.Application(
        routes,
        debug=config.get("_global_.tornado.debug", False),
        xsrf_cookies=config.get("_global_.tornado.xsrf", True),
        xsrf_cookie_kwargs=config.get("_global_.tornado.xsrf_cookie_kwargs", {}),
    )
    sentry_dsn = config.get("_global_.sentry.dsn")

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                TornadoIntegration(),
                AioHttpIntegration(),
                RedisIntegration(),
            ],
        )

    return app
