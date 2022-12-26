import datetime
import os
from typing import Any

import pytz

from common.config import config


class TenantConfig:
    def __init__(self, tenant):
        self.tenant = tenant

    def get_tenant_or_global_config_var(self, config_str, default=None) -> Any:
        """Get a config variable from the tenant config. If it doesn't
        exist, get it from the the SaaS global config. If it doesn't exist there either,
        return the default value

        :param config_str: dot-separated string of the config variable
        :param default: default value if the config variable doesn't exist in tenant or global config
        :return: _description_
        """
        if result := config.get_tenant_specific_key(config_str, self.tenant):
            return result

        return result if (result := config.get(f"_global_.{config_str}")) else default

    @property
    def application_admins(self) -> list[str]:
        application_admins = (
            config.get_tenant_specific_key("application_admin", self.tenant) or []
        )
        if isinstance(application_admins, str):
            application_admins = [application_admins]
        return application_admins

    @property
    def tenant_storage_base_path(self):
        global_path = os.path.expanduser(
            config.get(
                "_global_.tenant_storage.base_path", "/data/tenant_data/"
            ).format(tenant=self.tenant)
        )
        os.makedirs(os.path.dirname(global_path), exist_ok=True)
        if self.tenant in global_path:
            raise Exception("Tenant ID must not be in the base path")

        tenant_base_path = os.path.join(global_path, self.tenant)
        os.makedirs(tenant_base_path, exist_ok=True)
        return tenant_base_path

    @property
    def tenant_url(self):
        return config.get_tenant_specific_key("url", self.tenant)

    @property
    def tenant_base_url(self):
        return self.tenant_url.split("/")[2]

    @property
    def jwt_secret(self):
        return config.get_tenant_specific_key("secrets.jwt_secret", self.tenant)

    @property
    def auth_use_secure_cookies(self):
        return "https://" in self.tenant_url

    @property
    def auth_jwt_expiration_minutes(self):
        return self.get_tenant_or_global_config_var("jwt.expiration_minutes", 1200)

    @property
    def auth_jwt_expiration_datetime(self) -> datetime.datetime:
        return datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) + datetime.timedelta(
            minutes=self.auth_jwt_expiration_minutes
        )

    @property
    def auth_cookie_name(self):
        return self.get_tenant_or_global_config_var("auth.cookie.name", "noq_auth")

    @property
    def auth_cookie_httponly(self):
        return self.get_tenant_or_global_config_var("auth.cookie.httponly", True)

    @property
    def auth_cookie_samesite(self):
        return self.get_tenant_or_global_config_var("auth.cookie.samesite", True)

    @property
    def auth_get_user_by_workos(self):
        # TODO: Change default to False
        return self.get_tenant_or_global_config_var("auth.get_user_by_workos", False)

    @property
    def workos_api_key(self):
        return self.get_tenant_or_global_config_var("secrets.workos.api_key")

    @property
    def workos_client_id(self):
        return self.get_tenant_or_global_config_var("secrets.workos.client_id")

    @property
    def workos_redis_key(self):
        return self.get_tenant_or_global_config_var(
            "workos.user_to_group_mapping.redis_key",
            f"{self.tenant}_WORKOS_USER_TO_GROUP_MAPPING",
        )

    @property
    def workos_s3_key(self):
        return self.get_tenant_or_global_config_var(
            "workos.user_to_group_mapping.s3_key",
            "workos_user_to_group_mapping/workos_user_to_group_mapping_v1.json.gz",
        )

    @property
    def workos_group_attribute(self):
        return self.get_tenant_or_global_config_var(
            "workos.user_to_group_mapping.group_attribute", "group_names"
        )

    @property
    def saml_certificate_folder(self):
        return "saml_certificates"

    @property
    def saml_cert_path(self):
        return f"{self.saml_certificate_folder}/certs/sp.crt"

    @property
    def saml_key_path(self):
        return f"{self.saml_certificate_folder}/certs/sp.key"

    @property
    def saml_ca_key_path(self):
        return f"{self.saml_certificate_folder}/ca/key.pem"

    @property
    def scim_endpoint_authenticator(self):
        return self.get_tenant_specific_key(
            "secrets.scim.endpoint_authenticator", self.tenant
        )

    @property
    def scim_bearer_token(self):
        return self.get_tenant_specific_key("secrets.scim.bearer_token", self.tenant)

    @property
    def saml_key_passphrase(self):
        return self.jwt_secret.encode("utf-8")

    @property
    def saml_config(self):
        _saml_config = {
            "debug": True,
            "sp": {
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "assertionConsumerService": {
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                    "url": f"{self.tenant_url}/saml/acs",
                },
                "entityId": f"{self.tenant_url}",
                "singleLogoutService": {
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                    "url": f"{self.tenant_url}/saml/sls",
                },
            },
            "strict": False,
            "support": {
                "emailAddress": "support@noq.dev",
                "givenName": "Noq Support",
                "technical": {
                    "emailAddress": "support@noq.dev",
                    "givenName": "Noq Support",
                },
            },
            "organization": {
                "en-US": {
                    "displayname": "Noq",
                    "name": "Noq",
                    "url": self.tenant_url,
                }
            },
            "security": {
                "authnRequestsSigned": True,
                "digestAlgorithm": "http://www.w3.org/2000/09/xmldsig#sha1",
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "nameIdEncrypted": False,
                "signMetadata": False,
                "signatureAlgorithm": "http://www.w3.org/2000/09/xmldsig#rsa-sha1",
                "wantAssertionsEncrypted": False,
                "wantAssertionsSigned": False,
                "wantMessagesSigned": False,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
            },
        }

        if idp_config := config.get_tenant_specific_key(
            "get_user_by_saml_settings.idp", self.tenant
        ):
            _saml_config["idp"] = idp_config
            if not _saml_config["idp"].get("entityId"):
                _saml_config["idp"]["entityId"] = self.tenant_url
        return _saml_config

    @property
    def require_mfa(self):
        return self.get_tenant_or_global_config_var("auth.require_mfa", False)
