from datetime import datetime, timedelta

import pytz
from asgiref.sync import sync_to_async
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseHandler
from cloudumi_common.lib.jwt import generate_jwt_token
from cloudumi_common.lib.plugins import get_plugin_by_name
from cloudumi_common.lib.saml import init_saml_auth, prepare_tornado_request_for_saml

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
            not_auth_warn = not await sync_to_async(auth.is_authenticated)()
            if not_auth_warn:
                self.write("User is not authenticated")
                await self.finish()
                return
            if len(errors) == 0:

                saml_attributes = await sync_to_async(auth.get_attributes)()
                email = saml_attributes[
                    config.get(
                        f"site_configs.{host}.get_user_by_saml_settings.attributes.email"
                    )
                ]
                if isinstance(email, list) and len(email) > 0:
                    email = email[0]
                groups = saml_attributes.get(
                    config.get(
                        f"site_configs.{host}.get_user_by_saml_settings.attributes.groups"
                    ),
                    [],
                )

                self_url = await sync_to_async(OneLogin_Saml2_Utils.get_self_url)(req)
                expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
                    minutes=config.get(
                        f"site_configs.{host}.jwt.expiration_minutes", 60
                    )
                )
                encoded_cookie = await generate_jwt_token(
                    email, groups, host, exp=expiration
                )
                self.set_cookie(
                    "consoleme_auth",
                    encoded_cookie,
                    expires=expiration,
                    secure=config.get(
                        f"site_configs.{host}.auth.cookie.secure",
                        "https://" in config.get(f"site_configs.{host}.url"),
                    ),
                    httponly=config.get(
                        f"site_configs.{host}.auth.cookie.httponly", True
                    ),
                    samesite=config.get(
                        f"site_configs.{host}.auth.cookie.samesite", True
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
