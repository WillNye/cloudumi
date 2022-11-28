import hashlib
import time
from secrets import token_urlsafe
from urllib.parse import urlparse

import boto3
import sentry_sdk
import tornado.escape
import tornado.web
from email_validator import validate_email
from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import ImmutableSandboxedEnvironment

from api.handlers.v3.tenant_registration.models import NewTenantRegistration
from common.config import config
from common.handlers.base import TornadoRequestHandler
from common.lib.cognito.identity import (
    ADMIN_GROUP_NAME,
    CognitoUserClient,
    create_user_pool,
    create_user_pool_client,
    create_user_pool_domain,
    generate_dev_domain,
    get_external_id,
)
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.free_email_domains import is_email_free
from common.lib.tenant.models import TenantDetails

log = config.get_logger()


async def set_login_page_ui(user_pool_id):
    cognito = boto3.client("cognito-idp", region_name=config.region)
    env = ImmutableSandboxedEnvironment(
        loader=FileSystemLoader("common/templates"),
        extensions=["jinja2.ext.loopcontrols"],
        autoescape=select_autoescape(),
    )
    cognito_login_css_template = env.get_template("cognito_login_page.css.j2")
    cognito_login_css = cognito_login_css_template.render()
    nog_logo = open(
        config.get(
            "_global_.tenant_registration.set_login_page_ui.logo_location",
            "common/templates/NoqLogo.png",
        ),
        "rb",
    ).read()
    return cognito.set_ui_customization(
        UserPoolId=user_pool_id,
        ClientId="ALL",
        CSS=cognito_login_css,
        ImageFile=nog_logo,
    )


class TenantRegistrationAwsMarketplaceHandler(TornadoRequestHandler):
    async def post(self):
        body = tornado.escape.json_decode(self.request.body)
        amazon_marketplace_reg_token = body.get("x-amzn-marketplace-token")
        if not amazon_marketplace_reg_token:
            self.set_status(400)
            self.write({"error": "x-amzn-marketplace-token is required"})
            return
        # marketplace_client = boto3.client("meteringmarketplace")
        # customer_data = await aio_wrapper(marketplace_client.resolve_customer,
        #     amazon_marketplace_reg_token
        # )
        # customer_id = customer_data["CustomerIdentifier"]
        # Expected customer_id: {
        #     'CustomerIdentifier': 'string',
        #     'ProductCode': 'string'
        # }
        # TODO: Validate no other accounts share the same customerID
        # TODO: Store customer information
        # TODO: Should we give the user a signed cookie, then ask them to specify credentials / domain?


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

        # TODO: Check if email already registered
        # if await is_email_registered(data.get("email")):
        #     self.set_status(400)
        #     self.write(
        #         {
        #             "error": "Email already registered",
        #             "error_description": "The email is already registered",
        #         }
        #     )
        #     return

        # TODO: When we allow custom domain registrations, don't allow noq, registration, or anything else in the domain
        # name

        valid_registration_code = hashlib.sha256(
            "noq_tenant_{}".format(data.get("email")).encode()
        ).hexdigest()[0:20]
        # check if registration code is valid
        if data.get("registration_code") != valid_registration_code:
            self.set_status(400)
            self.write(
                {
                    "error": "Invalid registration code",
                    "error_description": "The registration code is invalid",
                }
            )
            return

        region = config.region
        # validate tenant
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

        dev_mode = config.get("_global_.development")
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

        cognito_url_domain = data.get("domain", "").replace(".", "-")
        dev_domain_url = f'https://{dev_domain.replace("_", ".")}'

        try:
            # create new tenant
            user_pool_id = await create_user_pool(dev_domain, dev_domain_url)
        except Exception as e:
            self.set_status(400)
            self.write(
                {
                    "error": f"Unable to create user pool {str(e)}",
                    "error_description": "Failed to create user pool. Please try again.",
                }
            )
            return

        try:
            user_pool_domain = await create_user_pool_domain(
                user_pool_id, cognito_url_domain
            )
        except Exception as e:
            # TODO: Remove the user pool because it is now orphaned
            self.set_status(400)
            self.write(
                {
                    "error": f"Unable to create user pool domain: {str(e)}",
                    "error_description": "Failed to create user pool domain. Please try again.",
                }
            )
            return

        if user_pool_domain["ResponseMetadata"]["HTTPStatusCode"] != 200:
            # TODO: Remove the user pool because it is now orphaned
            self.set_status(400)
            self.write(
                {
                    "error": "Unable to create user pool domain",
                    "error_description": "Failed to create user pool domain. Please try again.",
                }
            )
            return

        try:
            await set_login_page_ui(user_pool_id)
        except Exception as e:
            # it's not fatal not able to set logo...let's capture in log and continue
            sentry_sdk.capture_exception(e)

        (
            cognito_client_id,
            cognito_user_pool_client_secret,
        ) = await create_user_pool_client(user_pool_id, dev_domain_url)
        try:
            cognito_idp = CognitoUserClient(
                user_pool_id, cognito_client_id, cognito_user_pool_client_secret
            )
            await cognito_idp.create_init_user(tenant.email)
        except Exception as e:
            # TODO: Remove the user pool and domain because it is now orphaned
            self.set_status(400)
            self.write(
                {
                    "error": "Unable to create user pool user",
                    "error_description": str(e),
                }
            )
            sentry_sdk.capture_exception(e)
            return

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
application_admin: {ADMIN_GROUP_NAME}
secrets:
  jwt_secret: {token_urlsafe(32)}
  auth:
    oidc:
      client_id: {cognito_client_id}
      client_secret: {cognito_user_pool_client_secret}
  cognito:
    config:
        user_pool_id: {user_pool_id}
        user_pool_client_id: {cognito_client_id}
        user_pool_client_secret: {cognito_user_pool_client_secret}
        user_pool_region: {config.region}
get_user_by_oidc_settings:
  client_scopes:
    - email
    - openid
    - profile
    - aws.cognito.signin.user.admin
  resource: noq_tenant
  metadata_url: https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration
  jwt_verify: true
  jwt_email_key: email
  jwt_groups_key: 'custom:groups'
  grant_type: authorization_code
  id_token_response_key: id_token
  access_token_response_key: access_token
  access_token_audience: null
auth:
  extra_auth_cookies:
    - AWSELBAuthSessionCookie
  logout_redirect_url: https://{cognito_url_domain}.auth.{region}.amazoncognito.com/logout?client_id={cognito_client_id}&logout_uri={dev_domain_url}
  get_user_by_oidc: true
  force_redirect_to_identity_provider: false
  # get_user_by_password: true
  # get_user_by_cognito: true
"""

        # Store tenant information in DynamoDB
        await TenantDetails.create(dev_domain, tenant.email)

        ddb = RestrictedDynamoHandler()
        await ddb.update_static_config_for_tenant(
            tenant_config, tenant.email, dev_domain
        )
        self.write(
            {
                "success": True,
                "username": tenant.email,
                "domain": dev_domain_url,
            }
        )
