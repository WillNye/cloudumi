from datetime import datetime, timedelta

import pytz
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.asyncio import aio_wrapper
from common.lib.jwt import generate_jwt_token
from common.lib.plugins import get_plugin_by_name
from common.lib.saml import init_saml_auth, prepare_tornado_request_for_saml

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class SamlHandler(BaseHandler):
    def check_xsrf_cookie(self):
        pass

    async def post(self, endpoint):
        host = self.get_host_name()
        req = await prepare_tornado_request_for_saml(self.request)
        auth = await init_saml_auth(req, host)

        if "sso" in endpoint:
            return self.redirect(auth.login())
        elif "acs" in endpoint:
            auth.process_response()
            errors = auth.get_errors()
            not_auth_warn = not await aio_wrapper(auth.is_authenticated)
            if not_auth_warn:
                self.write("User is not authenticated")
                await self.finish()
                return
            if len(errors) == 0:

                saml_attributes = await aio_wrapper(auth.get_attributes)
                email = saml_attributes[
                    config.get_host_specific_key(
                        "get_user_by_saml_settings.attributes.email",
                        host,
                    )
                ]
                if isinstance(email, list) and len(email) > 0:
                    email = email[0]
                groups = saml_attributes.get(
                    config.get_host_specific_key(
                        "get_user_by_saml_settings.attributes.groups",
                        host,
                    ),
                    [],
                )

                self_url = await aio_wrapper(OneLogin_Saml2_Utils.get_self_url, req)
                expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
                    minutes=config.get_host_specific_key(
                        "jwt.expiration_minutes", host, 1200
                    )
                )
                encoded_cookie = await generate_jwt_token(
                    email, groups, host, exp=expiration
                )
                self.set_cookie(
                    config.get("_global_.auth.cookie.name", "consoleme_auth"),
                    encoded_cookie,
                    expires=expiration,
                    secure=config.get_host_specific_key(
                        "auth.cookie.secure",
                        host,
                        "https://" in config.get_host_specific_key("url", host),
                    ),
                    httponly=config.get_host_specific_key(
                        "auth.cookie.httponly", host, True
                    ),
                    samesite=config.get_host_specific_key(
                        "auth.cookie.samesite", host, True
                    ),
                )
                if (
                    "RelayState" in self.request.arguments
                    and self_url
                    != self.request.arguments["RelayState"][0].decode("utf-8")
                ):
                    return self.redirect(
                        auth.redirect_to(
                            self.request.arguments["RelayState"][0].decode("utf-8")
                        )
                    )
