import hashlib
import sys
import time
from secrets import token_urlsafe
from urllib.parse import urlparse

import furl
import sentry_sdk
import tornado.escape
import tornado.web
from email_validator import validate_email

from api.handlers.v3.tenant_registration.models import NewTenantRegistration
from common.config import config
from common.config.globals import ASYNC_PG_ENGINE
from common.group_memberships.models import GroupMembership
from common.groups.models import Group
from common.handlers.base import TornadoRequestHandler
from common.lib.cognito.identity import (
    ADMIN_GROUP_NAME,
    generate_dev_domain,
    generate_password,
    get_external_id,
)
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.free_email_domains import is_email_free
from common.lib.tenant.models import TenantDetails
from common.tenants.models import Tenant
from common.users.models import User

log = config.get_logger(__name__)


class TenantRegistrationAwsMarketplaceHandler(TornadoRequestHandler):
    async def post(self):
        body = tornado.escape.json_decode(self.request.body)
        amazon_marketplace_reg_token = body.get("x-amzn-marketplace-token")
        if not amazon_marketplace_reg_token:
            self.set_status(400)
            self.write({"error": "x-amzn-marketplace-token is required"})
            return


class TenantRegistrationHandler(TornadoRequestHandler):
    def set_default_headers(self):
        valid_referrers = ["localhost", "noq.dev", "www.noq.dev", "127.0.0.1"]
        referrer = self.request.headers.get("Referer")
        if referrer is not None:
            referrer_host = urlparse(referrer).hostname
            if referrer_host in valid_referrers:
                self.set_header("Access-Control-Allow-Origin", "*")
                self.set_header(
                    "Access-Control-Allow-Headers",
                    "content-type, x-requested-with, x-forwarded-host",
                )
                self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    async def options(self, *args):
        pass

    def check_xsrf_cookie(self) -> None:
        pass

    async def post(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Tenant registration POST request received",
        }
        log.debug(log_data)
        # Get the data from the request
        data = tornado.escape.json_decode(self.request.body)

        # Check if the data is valid
        if not data:
            self.set_status(400)
            self.write(
                {
                    "error": "Invalid data",
                    "error_description": "The data sent to the server is invalid",
                }
            )
            return

        # Validate email
        try:
            valid = validate_email(data.get("email"))
            if not valid:
                self.set_status(400)
                self.write(
                    {
                        "error": "Invalid email",
                        "error_description": "The email is invalid",
                    }
                )
                return
        except Exception:
            self.set_status(400)
            self.write(
                {
                    "error": "Invalid email",
                    "error_description": "The email is invalid",
                }
            )
            sentry_sdk.capture_exception()
            return

        # Check if e-mail is a free e-mail
        if await is_email_free(data.get("email")):
            self.set_status(400)
            self.write(
                {
                    "error": "Please enter a business e-mail address",
                    "error_description": "Please enter a business e-mail address",
                }
            )
            return

        log_data["email"] = data["email"]
        dev_mode = config.get("_global_.development")

        # Validate registration code
        valid_registration_code = hashlib.sha256(
            "noq_tenant_{}".format(data.get("email")).encode()
        ).hexdigest()[0:20]

        if not dev_mode:
            if data.get("registration_code") != valid_registration_code:
                self.set_status(400)
                self.write(
                    {
                        "error": "Invalid registration code",
                        "error_description": "The registration code is invalid",
                    }
                )
                return

        # Validate tenant
        try:
            tenant = NewTenantRegistration.parse_obj(data)
        except Exception as e:
            self.set_status(400)
            self.write(
                {
                    "error": "Invalid data",
                    "error_description": str(e),
                }
            )
            sentry_sdk.capture_exception(e)
            return

        dev_domain = data.get("domain", "").replace(".", "_")

        if dev_domain:
            if await TenantDetails.tenant_exists(dev_domain):
                self.set_status(400)
                self.write(
                    {
                        "error": f"The provided domain has already been registered ({dev_domain}). "
                        f"Please specify a different domain or contact your admin for next steps.",
                    }
                )
                return
        elif not dev_mode:  # Don't generate domains on prod
            self.set_status(400)
            self.write(
                {
                    "error": "A valid domain that has not already been registered must be provided."
                }
            )
            return
        else:
            # Generate a valid dev domain
            dev_domain = await generate_dev_domain(dev_mode)
            if not dev_domain:
                self.set_status(400)
                self.write(
                    {
                        "error": "Unable to generate a suitable domain",
                        "error_description": "Failed to generate a dev domain. Please try again.",
                    }
                )
                return

        # TODO: Validate domain ends in a valid suffix / or just the prefix, just get the subdomain

        dev_domain_url = f'https://{dev_domain.replace("_", ".")}'
        log_data["dev_domain"] = dev_domain
        log_data["dev_domain_url"] = dev_domain_url

        async with ASYNC_PG_ENGINE.begin():
            tenant_db = await Tenant.create(
                name=dev_domain,
                organization_id=dev_domain,
            )
            email_domain = tenant.email.split("@")[1]
            password = generate_password()
            user = await User.create(
                tenant_db,
                tenant.email,
                tenant.email,
                password,
                email_verified=True,
                managed_by="MANUAL",
            )
            group = await Group.create(
                tenant=tenant_db,
                name="noq_admins",
                email=f"noq_admins@{email_domain}",
                description="Noq Admins",
                managed_by="MANUAL",
            )
            await GroupMembership.create(user, group)

        external_id = await get_external_id(dev_domain, tenant.email)

        tenant_config = f"""
cloud_credential_authorization_mapping:
  role_tags:
    enabled: false
    authorized_groups_tags:
      - noq_authorized
    authorized_groups_cli_only_tags:
      - noq_authorized_cli
challenge_url:
  enabled: true
environment: prod
tenant_details:
  external_id: {external_id}
  creator: {tenant.email}
  creation_time: {int(time.time())}
site_config:
  landing_url: /
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
url: {dev_domain_url}
application_admin:
  - {ADMIN_GROUP_NAME}
secrets:
  jwt_secret: {token_urlsafe(32)}
auth:
  extra_auth_cookies:
    - AWSELBAuthSessionCookie
  force_redirect_to_identity_provider: false
"""

        # Store tenant information in DynamoDB
        await TenantDetails.create(dev_domain, tenant.email)

        ddb = RestrictedDynamoHandler()
        await ddb.update_static_config_for_tenant(
            tenant_config, tenant.email, dev_domain
        )

        await user.send_password_via_email(
            dev_domain,
            furl.furl(dev_domain_url),
            password,
        )
        return_data = {
            "success": True,
            "username": tenant.email,
            "domain": dev_domain_url,
        }

        # For our functional tests, we want to return the password
        if config.get("_global_.environment") in ["dev", "staging"]:
            # Make sure dev_domain_url starts with `test_`
            if dev_domain_url.startswith("https://test-") and (
                dev_domain_url.endswith(".staging.noq.dev")
                or dev_domain_url.endswith(".example.com")
            ):
                # Make sure self.request.host is localhost
                if self.request.host == "localhost:8092":
                    # Make sure email starts with `cypress_ui_saas_functional_tests+` and ends in `@noq.dev`
                    email_prefix = "cypress_ui_saas_functional_tests+"
                    email_suffix = "@noq.dev"
                    if tenant.email.startswith(email_prefix) and tenant.email.endswith(
                        email_suffix
                    ):
                        return_data["password"] = password
        log_data["message"] = "Tenant registration POST request processed successfully"
        log.debug(log_data)
        self.write(return_data)

    async def delete(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Tenant registration DELETE request received",
        }
        log.debug(log_data)
        environment = config.get("_global_.environment")
        if environment not in ["dev", "staging"]:
            self.set_status(403)
            self.write(
                {
                    "error": "This endpoint is only allowed in dev and staging environments."
                }
            )
            return

        data = tornado.escape.json_decode(self.request.body)
        email = data.get("email")

        if email is None:
            self.set_status(400)
            self.write({"error": "Email is required."})
            return

        email_prefix = "cypress_ui_saas_functional_tests+"
        email_suffix = "@noq.dev"

        if not (email.startswith(email_prefix) and email.endswith(email_suffix)):
            self.set_status(403)
            self.write(
                {
                    "error": "This endpoint only allows deletion of tenants used for functional tests."
                }
            )
            return

        dev_domain_url = data.get("domain", "")

        dev_domain = dev_domain_url.replace(".", "_")

        if not dev_domain:
            self.set_status(400)
            self.write({"error": "A valid domain must be provided."})
            return

        if not (
            dev_domain_url.startswith("test-")
            and (
                dev_domain_url.endswith(".staging.noq.dev")
                or dev_domain_url.endswith(".example.com")
            )
        ):
            self.set_status(403)
            self.write(
                {
                    "error": "This endpoint only allows deletion of tenants used for functional tests."
                }
            )
            return

        async with ASYNC_PG_ENGINE.begin():
            tenant = await Tenant.get_by_name(dev_domain)
            if tenant is not None:
                await tenant.delete()

        ddb = RestrictedDynamoHandler()
        await ddb.delete_static_config_for_tenant(dev_domain)

        tenant_details = await TenantDetails.get(dev_domain)

        await TenantDetails.delete(tenant_details)

        self.write({"success": True, "message": f"Tenant {dev_domain} deleted."})
        log_data[
            "message"
        ] = "Tenant registration DELETE request processed successfully"
        log.debug(log_data)
