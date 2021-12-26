import base64
import hashlib
import hmac
import random
from datetime import datetime
from secrets import token_urlsafe
from typing import List
from urllib.parse import urlparse

import boto3
import sentry_sdk
import tornado.escape
import tornado.web
from email_validator import validate_email
from password_strength import PasswordPolicy

from api.handlers.v3.tenant_registration.models import NewTenantRegistration
from common.config import config
from common.handlers.base import TornadoRequestHandler
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.free_email_domains import is_email_free


async def generate_dev_domain(dev_mode):
    tenant_id = random.randint(000000, 999999)
    if dev_mode:
        suffix = "noq_localhost"
    else:
        suffix = "noq_dev"
    return f"dev-{tenant_id}_{suffix}"


async def create_user_pool(noq_subdomain):
    cognito = boto3.client("cognito-idp")
    # a = cognito.describe_user_pool(UserPoolId="us-east-1_nvTFqJY2L")
    # print(a)
    # b = cognito.describe_user_pool_client(UserPoolId="us-east-1_nvTFqJY2L", ClientId="1fpq9om50b4bm1225o8it875jj")
    paginator = cognito.get_paginator("list_user_pools")
    response_iterator = paginator.paginate(
        PaginationConfig={"MaxItems": 60, "PageSize": 60}
    )

    user_pool_name = "cloudumi_tenant_" + noq_subdomain

    user_pool_already_exists = False
    for response in response_iterator:
        for user_pool in response["UserPools"]:
            if user_pool["Name"] == user_pool_name:
                user_pool_already_exists = True
                break
    if user_pool_already_exists:
        print("User pool already exists")
        raise Exception("User Pool Already Exists")
    # COGNITO: You need a custom domain too
    response = cognito.create_user_pool(
        PoolName=user_pool_name,
        Schema=[
            {
                "Name": "sub",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": False,
                "Required": True,
                "StringAttributeConstraints": {"MinLength": "1", "MaxLength": "2048"},
            },
            {
                "Name": "name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "given_name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "family_name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "middle_name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "nickname",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "preferred_username",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "profile",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "picture",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "website",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "email",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": True,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "email_verified",
                "AttributeDataType": "Boolean",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
            },
            {
                "Name": "gender",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "birthdate",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "10", "MaxLength": "10"},
            },
            {
                "Name": "zoneinfo",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "locale",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "phone_number",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "address",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "updated_at",
                "AttributeDataType": "Number",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "NumberAttributeConstraints": {"MinValue": "0"},
            },
            {
                "Name": "identities",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {},
            },
        ],
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": True,
                "RequireLowercase": True,
                "RequireNumbers": True,
                "RequireSymbols": True,
            }
        },
        AutoVerifiedAttributes=["email"],
        EmailConfiguration={"EmailSendingAccount": "COGNITO_DEFAULT"},
        UsernameAttributes=["email"],
        # AliasAttributes=[
        #     'email',
        #     'preferred_username'
        # ],
        UserPoolTags={"tenant": noq_subdomain},
        AdminCreateUserConfig={
            "AllowAdminCreateUserOnly": False,
            "UnusedAccountValidityDays": 7,
        },
        # TODO: Enable advanced security mode
        # UserPoolAddOns={
        #     'AdvancedSecurityMode': 'ENFORCED'
        # },
        UsernameConfiguration={"CaseSensitive": False},
        AccountRecoverySetting={
            "RecoveryMechanisms": [
                {"Priority": 1, "Name": "verified_email"},
            ]
        },
        VerificationMessageTemplate={
            "DefaultEmailOption": "CONFIRM_WITH_LINK",
        },
    )
    return response["UserPool"]["Id"]


async def get_secret_hash(username, client_id, client_secret):
    msg = username + client_id
    dig = hmac.new(
        str(client_secret).encode("utf-8"),
        msg=str(msg).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(dig).decode()


async def get_external_id(host, username):
    dig = hmac.new(
        str(host).encode("utf-8"),
        msg=str(username).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return dig


async def create_user_pool_user(
    user_pool_client_id, client_secret, email, password, noq_subdomain
):
    cognito = boto3.client("cognito-idp")

    user = cognito.sign_up(
        ClientId=user_pool_client_id,
        SecretHash=await get_secret_hash(email, user_pool_client_id, client_secret),
        Username=email,
        Password=password,
        UserAttributes=[
            {"Name": "email", "Value": email},
        ],
    )

    # user = cognito.admin_create_user(
    #     UserPoolId=user_pool_id,
    #     Username=email,
    #     UserAttributes=[
    #         {
    #             'Name': 'email',
    #             'Value': email
    #         },
    #         # {
    #         #     'Name': 'email_verified',
    #         #     'Value': "true"
    #         # }
    #         ],
    #     DesiredDeliveryMediums=[
    #         'EMAIL',
    #     ],
    # )
    return user


async def create_user_pool_client(user_pool_id, dev_domain_url):
    cognito = boto3.client("cognito-idp")
    res = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName="noq_tenant",
        GenerateSecret=True,
        RefreshTokenValidity=1,
        AccessTokenValidity=60,
        IdTokenValidity=60,
        TokenValidityUnits={
            "AccessToken": "minutes",
            "IdToken": "minutes",
            "RefreshToken": "days",
        },
        ReadAttributes=[
            "address",
            "birthdate",
            "email",
            "email_verified",
            "family_name",
            "gender",
            "given_name",
            "locale",
            "middle_name",
            "name",
            "nickname",
            "phone_number",
            "phone_number_verified",
            "picture",
            "preferred_username",
            "profile",
            "updated_at",
            "website",
            "zoneinfo",
        ],
        WriteAttributes=[
            "address",
            "birthdate",
            "email",
            "family_name",
            "gender",
            "given_name",
            "locale",
            "middle_name",
            "name",
            "nickname",
            "phone_number",
            "picture",
            "preferred_username",
            "profile",
            "updated_at",
            "website",
            "zoneinfo",
        ],
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=[
            "ALLOW_CUSTOM_AUTH",
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_USER_SRP_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
        ],
        CallbackURLs=[
            f"{dev_domain_url}/auth",
            f"{dev_domain_url}/oauth2/idpresponse",
        ],
        LogoutURLs=[
            # f'{dev_domain_url}/logout',
        ],
        # DefaultRedirectURI=f'{dev_domain_url}/',
        AllowedOAuthFlows=[
            "code",
        ],
        AllowedOAuthScopes=["email", "openid", "profile"],
        AllowedOAuthFlowsUserPoolClient=True,
        PreventUserExistenceErrors="ENABLED",
        EnableTokenRevocation=True,
    )
    return res["UserPoolClient"]["ClientId"], res["UserPoolClient"]["ClientSecret"]


async def create_user_pool_domain(user_pool_id, user_pool_domain_name):
    cognito = boto3.client("cognito-idp")
    user_pool_domain = cognito.create_user_pool_domain(
        UserPoolId=user_pool_id, Domain=user_pool_domain_name
    )
    return user_pool_domain


class TenantRegistrationAwsMarketplaceHandler(TornadoRequestHandler):
    async def post(self):
        body = tornado.escape.json_decode(self.request.body)
        amazon_marketplace_reg_token = body.get("x-amzn-marketplace-token")
        if not amazon_marketplace_reg_token:
            self.set_status(400)
            self.write({"error": "x-amzn-marketplace-token is required"})
            return
        # marketplace_client = boto3.client("meteringmarketplace")
        # customer_data = await sync_to_async(marketplace_client.resolve_customer)(
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

        password = data.get("password")
        policy = PasswordPolicy.from_names(
            length=8,
            uppercase=1,
            numbers=1,
            special=1,
            nonletters=1,
        )

        tested_pass = policy.password(password)
        errors = tested_pass.test()
        # Convert errors to string so they can be json encoded later
        errors: List[str] = [str(e) for e in errors]

        if errors:
            self.set_status(400)
            self.write(
                {
                    "error": "The password is not complex enough.",
                    "errors": errors,
                }
            )
            return

        # TODO: Make region configurable
        region = "us-east-1"
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
        # Generate a valid dev domain
        dev_domain = await generate_dev_domain(dev_mode)
        available = False
        for i in range(0, 10):
            # check if the dev domain is available
            if not config.get_tenant_static_config_from_dynamo(dev_domain):
                available = True
                break
            dev_domain = await generate_dev_domain(dev_mode)

        # User pool domain names cannot have underscores
        user_pool_domain_name = dev_domain.replace("_", "-")

        if not available:
            self.set_status(400)
            self.write(
                {
                    "error": "Unable to generate a suitable domain",
                    "error_description": "Failed to generate a dev domain. Please try again.",
                }
            )
            return
        if dev_mode:
            uri_scheme = "https://"
            port = ""
            # port = ":3000"
        else:
            uri_scheme = "https://"
            port = ""
        dev_domain_url = uri_scheme + dev_domain.replace("_", ".") + port
        # create new tenant
        user_pool_id = await create_user_pool(dev_domain)
        user_pool_domain = await create_user_pool_domain(
            user_pool_id, user_pool_domain_name
        )
        if user_pool_domain["ResponseMetadata"]["HTTPStatusCode"] != 200:
            self.set_status(400)
            self.write(
                {
                    "error": "Unable to create user pool domain",
                    "error_description": "Failed to create user pool domain. Please try again.",
                }
            )
            return

        (
            cognito_client_id,
            cognito_user_pool_client_secret,
        ) = await create_user_pool_client(user_pool_id, dev_domain_url)
        try:
            await create_user_pool_user(
                cognito_client_id,
                cognito_user_pool_client_secret,
                tenant.email,
                tenant.password,
                dev_domain,
            )
        except Exception as e:
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
  creation_time: {datetime.now().isoformat()}
site_config:
  landing_url: /settings
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
identity:
  cache_groups:
    enabled: true
  identity_providers:
    okta_test:
      name: okta_test
      idp_type: okta
      org_url: https://dev-876967.okta.com/
      # TODO: No secrets should be in plaintext configuration
      api_token: 00T8xmegwdOppNEJxE33AyGg7EG3nIQAeHcUmmPb2u
url: {dev_domain_url}
application_admin: {tenant.email}
secrets:
  jwt_secret: {token_urlsafe(32)}
  auth:
    oidc:
      client_id: {cognito_client_id}
      client_secret: {cognito_user_pool_client_secret}
get_user_by_oidc_settings:
  client_scopes:
    - email
    - openid
  resource: noq_tenant
  metadata_url: https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration
  jwt_verify: true
  jwt_email_key: email
  jwt_groups_key: "cognito:groups"
  grant_type: authorization_code
  id_token_response_key: id_token
  access_token_response_key: access_token
  access_token_audience: null
auth:
  get_user_by_oidc: true
  force_redirect_to_identity_provider: false
  # get_user_by_password: true
  # get_user_by_cognito: true
  cognito_config:
    user_pool_id: {user_pool_id}
    user_pool_client_id: {cognito_client_id}
    user_pool_client_secret: {cognito_user_pool_client_secret}
"""

        # Store tenant information in DynamoDB

        ddb = RestrictedDynamoHandler()

        await ddb.update_static_config_for_host(tenant_config, tenant.email, dev_domain)
        self.write(
            {
                "success": True,
                "username": tenant.email,
                "domain": dev_domain_url,
            }
        )
