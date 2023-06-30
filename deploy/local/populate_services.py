import asyncio
import multiprocessing
import os
import sys
import time
import traceback
from secrets import token_urlsafe

import boto3
from asgiref.sync import async_to_sync

from common.config import config
from common.config.config import dict_merge
from common.config.globals import GITHUB_APP_ID
from common.github.models import GitHubInstall
from common.github.webhook_event_buffer import (
    allow_sns_to_write_to_sqs,
    get_developer_queue_arn,
    get_developer_queue_name,
)
from common.lib.aws.aws_secret_manager import get_aws_secret
from common.lib.yaml import yaml
from common.scripts.data_migrations import run_data_migrations
from common.tenants.models import Tenant

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")
override_email = os.getenv("OVERRIDE_EMAIL", "user@noq.dev")

import common.scripts.initialize_dynamodb  # noqa: F401, E402
from common.lib.dynamo import RestrictedDynamoHandler  # noqa: F401, E402

# We store sensitive secrets in AWS Secrets Manager. For example,
# Iambic repo configuration.
# We fetch these secrets and merge them into Tenant configuration
tenant_secrets_arn = "arn:aws:secretsmanager:us-west-2:759357822767:secret:dev/tenant_secrets_configuration-HcMJCi"
tenant_secrets = yaml.load(get_aws_secret(tenant_secrets_arn))

# before we place the repo value directly via secret manager for this PR,
# i am going to validate via directly changing it in code
# FIXME once we are cool with the PR, either update it via secret manager
# or just replace this whole tenant_secrets mechanism because repo_name is not much of secret
tenant_secrets["iambic_repos"][0]["repo_name"] = "noqdev/iambic-templates"
GITHUB_APP_ID_FOR_DEFAULT_LOCAL_DEV = config.get(
    "_global_.integrations.github.local_dev.app_id"
)
assert GITHUB_APP_ID_FOR_DEFAULT_LOCAL_DEV
DEV_IAMBIC_TEMPLATES_INSTALLATION_ID = config.get(
    "_global_.integrations.github.local_dev.installation_id"
)
assert DEV_IAMBIC_TEMPLATES_INSTALLATION_ID


GITHUB_APP_NOQ_DEV_WEBHOOK_SNS_ARN = (
    "arn:aws:sns:us-west-2:759357822767:github-app-noq-webhook"
)


loop = asyncio.get_event_loop()

localhost_tenant_config_raw = f"""
_development_user_override: {override_email}
_development_run_celery_tasks_1_min: true
_development_groups_override:
  - engineering@noq.dev
  - noq_admins
  - {override_email}
cloudtrail:
  enabled: true
  account_id: "759357822767"
  queue_arn: arn:aws:sqs:us-west-2:759357822767:noq-cloudtrail-access-denies
cache_self_service_typeahead:
  cache_resource_templates: true
groups:
  can_admin:
    - noq_admins
cache_resource_templates:
  repositories:
    - type: git
      main_branch_name: master
      name: consoleme
      repo_url: https://github.com/Netflix/consoleme
      web_path: https://github.com/Netflix/consoleme
      resource_formats:
        - terraform
      authentication_settings:
        email: "terraform@noq.dev"
      resource_type_parser: null
      terraform:
        path_suffix: .tf
cloud_credential_authorization_mapping:
  role_tags:
    authorized_groups_cli_only_tags:
      - noq-authorized-cli-only
    authorized_groups_tags:
      - noq-authorized
    enabled: true
challenge_url:
  enabled: true
environment: dev
hub_account:
  name: NoqCentralRoleLocalDev
  account_id: '759357822767'
  account_name: 'development'
  role_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
policies:
  role_name: NoqSpokeRoleLocalDev
spoke_accounts:
  - name: NoqSpokeRoleLocalDev
    account_name: 'development'
    account_id: '759357822767'
    role_arn: arn:aws:iam::759357822767:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
  - name: NoqSpokeRoleLocalDev
    account_name: development_2
    account_id: '350876197038'
    role_arn: arn:aws:iam::350876197038:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
  - name: NoqSpokeRoleLocalDev
    account_name: staging
    account_id: '259868150464'
    role_arn: arn:aws:iam::259868150464:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
  - name: NoqSpokeRoleLocalDev
    account_name: aws_org2_readonly
    account_id: '793450268703'
    role_arn: arn:aws:iam::793450268703:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
    read_only: true
temporary_role_access_requests:
  enabled: true
  mfa:
    enabled: false
tenant_details:
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
  creator: {override_email}
  creation_time: {int(time.time())}
notifications:
  enabled: false
site_config:
  landing_url: /
  request_interval: 1
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
url: https://localhost:3000
application_admin:
  - engineering@noq.dev
  - curtis@noq.dev
secrets:
  jwt_secret: {token_urlsafe(32)}
  scim:
    bearer_token: local_secret_scim_bearer_token
  auth:
    oidc:
      client_id: j14h62of81s6s5f2ivfkdfe3v
      client_secret: 1l4g523pb7rb3iicm9jod80nlst3r92f4oitg2dijna45pegj4dh
  cognito:
    config:
      user_pool_id: us-east-1_CNoZribID
      user_pool_region: us-east-1
      user_pool_client_id: j14h62of81s6s5f2ivfkdfe3v
      user_pool_client_secret: 1l4g523pb7rb3iicm9jod80nlst3r92f4oitg2dijna45pegj4dh
    jwt_auth:
      user_pool_id: us-east-1_CNoZribID
      user_pool_region: us-east-1
      user_pool_client_id: 6f44pcgu8dk978njp3frkt9p1k
account_ids_to_name:
  "759357822767": "development"
celery:
  cache_cloudtrail_denies:
    enabled: true
  sync_regions:
    - us-east-1
    - us-west-2
policy_request_autoapprove_rules:
  enabled: true
  rules:
    - name: auto_approve_low_risk_s3
      description: |-
        This auto-approval rule automatically approves requests
        to pre-approved S3 buckets
      policy: |-
        {{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Action": [
                        "s3:getobject",
                        "s3:getobjectacl",
                        "s3:getobjecttagging",
                        "s3:getobjectversion",
                        "s3:getobjectversionacl",
                        "s3:getobjectversiontagging",
                        "s3:listbucket",
                        "s3:listbucketversions"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::adostoma",
                        "arn:aws:s3:::adostoma/*",
                        "arn:aws:s3:::aenkvee",
                        "arn:aws:s3:::aenkvee/*"
                    ],
                    "Sid": "noquser1657458402wsng"
                }}
            ]
        }}
"""

localhost_tenant_config = yaml.load(localhost_tenant_config_raw)
dict_merge(localhost_tenant_config, tenant_secrets)
tenant_config = yaml.dump(localhost_tenant_config)

# Store tenant information in DynamoDB

ddb = RestrictedDynamoHandler()

async_to_sync(ddb.update_static_config_for_tenant)(
    tenant_config, override_email, "localhost"
)

cloudumi_config_raw = f"""
cache_self_service_typeahead:
  cache_resource_templates: true
cloudtrail:
  enabled: true
  account_id: "759357822767"
  queue_arn: arn:aws:sqs:us-west-2:759357822767:noq-cloudtrail-access-denies
cache_resource_templates:
  repositories:
    - type: git
      main_branch_name: master
      name: consoleme
      repo_url: https://github.com/Netflix/consoleme
      web_path: https://github.com/Netflix/consoleme
      resource_formats:
        - terraform
      authentication_settings:
        email: "terraform@noq.dev"
      resource_type_parser: null
      terraform:
        path_suffix: .tf
cloud_credential_authorization_mapping:
  role_tags:
    authorized_groups_cli_only_tags:
      - noq-authorized-cli-only
    authorized_groups_tags:
      - noq-authorized
    enabled: true
challenge_url:
  enabled: true
environment: dev
hub_account:
  name: NoqCentralRoleLocalDev
  account_id: '759357822767'
  account_name: 'development'
  role_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
policies:
  role_name: NoqSpokeRoleLocalDev
  ip_restrictions: false
temporary_role_access_requests:
  enabled: true
  mfa:
    enabled: false
spoke_accounts:
  - name: NoqSpokeRoleLocalDev
    account_name: 'development'
    account_id: '759357822767'
    role_arn: arn:aws:iam::759357822767:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
  - name: NoqSpokeRoleLocalDev
    account_name: development_2
    account_id: '350876197038'
    role_arn: arn:aws:iam::350876197038:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
  - name: NoqSpokeRoleLocalDev
    account_name: staging
    account_id: '259868150464'
    role_arn: arn:aws:iam::259868150464:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
  - name: NoqSpokeRoleLocalDev
    account_name: aws_org2_readonly
    account_id: '793450268703'
    role_arn: arn:aws:iam::793450268703:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
    read_only: true
tenant_details:
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
  creator: {override_email}
  creation_time: {int(time.time())}
notifications:
  enabled: false
site_config:
  landing_url: /
  request_interval: 1
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
url: https://cloudumidev.com:3000
application_admin:
  - engineering@noq.dev
  - noq_admins
secrets:
  scim:
    bearer_token: local_secret_scim_bearer_token
  jwt_secret: {token_urlsafe(32)}
  auth:
    oidc:
      client_id: '6f44pcgu8dk978njp3frkt9p1k'
  cognito:
    config:
      user_pool_id: 'us-east-1_CNoZribID'
      user_pool_client_id: '6f44pcgu8dk978njp3frkt9p1k'
      user_pool_region: 'us-east-1'
account_ids_to_name:
  "759357822767": "development"
auth:
  extra_auth_cookies:
    - AWSELBAuthSessionCookie
  logout_redirect_url: https://cloudumidev-com.auth.us-west-2.amazoncognito.com/logout?client_id=3vqhl3rfcfoqhl88g47norqick&logout_uri=https://cloudumidev.com:3000
  challenge_url:
    enabled: true
  get_user_by_oidc: true
  require_mfa: true
get_user_by_oidc_settings:
  custom_role_attributes:
    - name: 'custom:role_arns'
      delimiter: ','
      regex: '(.*)'
      role_match: '\\1'
  client_scopes:
    - email
    - openid
    - profile
    - aws.cognito.signin.user.admin
  resource: noq_tenant
  metadata_url: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_CNoZribID/.well-known/openid-configuration
  # metadata_url: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EQ5XHIluC/.well-known/openid-configuration
  jwt_verify: true
  jwt_email_key: email
  jwt_groups_key: "cognito:groups"
  grant_type: authorization_code
  id_token_response_key: id_token
  access_token_response_key: access_token
  access_token_audience: null
aws:
  automatically_update_role_trust_policies: false
celery:
  cache_cloudtrail_denies:
    enabled: true
  sync_regions:
    - us-east-1
    - us-west-2
policy_request_autoapprove_rules:
  enabled: true
  rules:
    - name: auto_approve_low_risk_s3
      description: |-
        This auto-approval rule automatically approves requests
        to pre-approved S3 buckets
      policy: |-
        {{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Action": [
                        "s3:getobject",
                        "s3:getobjectacl",
                        "s3:getobjecttagging",
                        "s3:getobjectversion",
                        "s3:getobjectversionacl",
                        "s3:getobjectversiontagging",
                        "s3:listbucket",
                        "s3:listbucketversions"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::adostoma",
                        "arn:aws:s3:::adostoma/*",
                        "arn:aws:s3:::aenkvee",
                        "arn:aws:s3:::aenkvee/*"
                    ],
                    "Sid": "noquser1657458402wsng"
                }}
            ]
        }}
"""
# Store cloudumidev information in DynamoDB
cloudumidev_tenant_config = yaml.load(cloudumi_config_raw)
dict_merge(cloudumidev_tenant_config, tenant_secrets)
cloudumi_config = yaml.dump(cloudumidev_tenant_config)


async_to_sync(ddb.update_static_config_for_tenant)(
    cloudumi_config, override_email, "cloudumidev_com"
)

cloudumi_saml_config = f"""
_development_groups_override:
  - engineering@noq.dev
cache_self_service_typeahead:
  cache_resource_templates: true
cloudtrail:
  enabled: true
  account_id: "759357822767"
  queue_arn: arn:aws:sqs:us-west-2:759357822767:noq-cloudtrail-access-denies
cache_resource_templates:
  repositories:
    - type: git
      main_branch_name: master
      name: consoleme
      repo_url: https://github.com/Netflix/consoleme
      web_path: https://github.com/Netflix/consoleme
      resource_formats:
        - terraform
      authentication_settings:
        email: "terraform@noq.dev"
      resource_type_parser: null
      terraform:
        path_suffix: .tf
cloud_credential_authorization_mapping:
  role_tags:
    authorized_groups_cli_only_tags:
      - noq-authorized-cli-only
    authorized_groups_tags:
      - noq-authorized
    enabled: true
challenge_url:
  enabled: true
environment: dev
hub_account:
  name: NoqCentralRoleLocalDev
  account_id: '759357822767'
  account_name: 'development'
  role_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
policies:
  role_name: NoqSpokeRoleLocalDev
  ip_restrictions: false
temporary_role_access_requests:
  enabled: true
  mfa:
    enabled: false
spoke_accounts:
  - name: NoqSpokeRoleLocalDev
    account_name: 'development'
    account_id: '759357822767'
    role_arn: arn:aws:iam::759357822767:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
  - name: NoqSpokeRoleLocalDev
    account_name: development_2
    account_id: '350876197038'
    role_arn: arn:aws:iam::350876197038:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
  - name: NoqSpokeRoleLocalDev
    account_name: staging
    account_id: '259868150464'
    role_arn: arn:aws:iam::259868150464:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
  - name: NoqSpokeRoleLocalDev
    account_name: aws_org2_readonly
    account_id: '793450268703'
    role_arn: arn:aws:iam::793450268703:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    org_management_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
    read_only: true
tenant_details:
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
  creator: {override_email}
  creation_time: {int(time.time())}
notifications:
  enabled: false
site_config:
  landing_url: /
  request_interval: 1
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
url: https://cloudumisamldev.com:3000
application_admin: engineering@noq.dev
secrets:
  jwt_secret: {token_urlsafe(32)}
  auth:
    oidc:
      client_id: '3vqhl3rfcfoqhl88g47norqick'
      client_secret: 'u6k40gpgkjkltcsk03040e3n848gppp0h066nh55f1k1ftltmjp'
  cognito:
    config:
      user_pool_id: 'us-west-2_EQ5XHIluC'
      user_pool_client_id: '3vqhl3rfcfoqhl88g47norqick'
      user_pool_client_secret: 'u6k40gpgkjkltcsk03040e3n848gppp0h066nh55f1k1ftltmjp'
      user_pool_region: 'us-west-2'
account_ids_to_name:
  "759357822767": "development"
auth:
  extra_auth_cookies:
    - AWSELBAuthSessionCookie
  logout_redirect_url: https://cloudumidev-com.auth.us-west-2.amazoncognito.com/logout?client_id=3vqhl3rfcfoqhl88g47norqick&logout_uri=https://cloudumidev.com:3000
  challenge_url:
    enabled: true
  get_user_by_saml: true
get_user_by_saml_settings:
  # On the provider, set ACS url to https://your_noq_url/saml/acs and saml audience to "https://your_noq_url/"
  # idp_metadata_url: "https://portal.sso.us-east-1.amazonaws.com/saml/metadata/MjU5ODY4MTUwNDY0X2lucy1lZmFkNjY2OTAzYmVlYTVh"
  jwt:
    expiration_hours: 1
    email_key: email
    groups_key: groups
  attributes:
    user: user
    groups: groups
    email: email
  idp:
    entityId: https://cloudumisamldev.com:3000
    singleSignOnService:
      binding: urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST
      url: https://sso.jumpcloud.com/saml2/cloudumisamldev
    x509cert: MIIFcjCCA1qgAwIBAgIUFy1o4VwDJsCDbVH1AEE8jnfZ/D8wDQYJKoZIhvcNAQELBQAwcTELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAkNPMRAwDgYDVQQHEwdCb3VsZGVyMQwwCgYDVQQKEwNOb3ExGTAXBgNVBAsTEEp1bXBDbG91ZFNBTUxJZFAxGjAYBgNVBAMTEUp1bXBDbG91ZFNBTUxVc2VyMB4XDTIyMTEyNjAwMTMxMloXDTI3MTEyNjAwMTMxMlowcTELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAkNPMRAwDgYDVQQHEwdCb3VsZGVyMQwwCgYDVQQKEwNOb3ExGTAXBgNVBAsTEEp1bXBDbG91ZFNBTUxJZFAxGjAYBgNVBAMTEUp1bXBDbG91ZFNBTUxVc2VyMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA3xzD6osFc1l/FkoFjYbnhIMdM50AqB8OYQ7/29X/+Q96nbly8rBb+Wj+4bmFJSJgNRUbNu2xVMf/e7XR/XY167DLvqAyxni3xmqwvWAWUiUTwQaLxtFDkOi+Lg4/lhSswP+zUdzZtNXnEEGjZWWLL+RlVU8sjFQdmVUsFg66SCqVSC9WO2mUqli2D6PM+wcCPgZTyhj/6sgVS8WJrvzCaTi5BuPy9eucIc+2cdPYxn/y40fAiGRTUENa1goQWUL3hSFXhZ8IsWBFwUbuX7bl3afRZmLA/WJzucztEdm0gneOtLrpsRkz76gm5udxX+Iw+0fnBwgWfbzfaXgp3BqRyKg57hb7M/7cmeBQgFg5hI8ka5EQ3zbe++UrW+zr08fqFrxe1yAhPpBHwD1/PDUp7SvZDQS5xRd9ohvtJJ1WXATASHT3CTEXPF6MFuC/GUtlizGvYVnyzzw48rftnk0Qb+OhLLt+yxQPyknpQm3JlQc6KY9FG4f7iYMS5v5a/kzs+DUf0k/Odn1YoYmC55iJWtoGMGhmuj5FFGD5Ow0qOr+OiiDoLhmqCS2zuie6y5T4dCTdqFWdintmelJthy7jPVZcPIl/rdU5aNgLwLxabg1bRQBtk6bCPzMQF5V4Bk0efFuTjBdO4CumIAKItNO/RrBdV3XI0AmjFeKaGmFXg1kCAwEAAaMCMAAwDQYJKoZIhvcNAQELBQADggIBAIHpq5GXCk5GW6tRiXdcgVkPxPJ0XEZPAPJcZWqvlftbgVy6IOobP9bm9+knUHW5c2lA0XVULiu6zSjr7/W1RHKZYuZYTdJy34WyN2GwWXMtbn2g9F/zz01c+nDJ80ZQ+cbjG9GkibjPxx0gVM3yOo/SnQT4PsNgeOObmieblAgk57jTzJ/NrNxF75jfdMdRUQ7CkMAKf4ceF2gV4Tsk/3cVVbB0XgNBcIw+fRMlu95YJ3W8WGVK1qzTeWxT4Jov2vxd9h7RAe42QOfsxMycwe84+chBQ8gVBdvivPiNwO3D8MqYKTN0VMDbaAorrnRY+NQrenXVXAoRPB9fNc6OjoFRUETPG9syXdlS0CMt5PZkI128m32do7pQjOwFK3dzrpkPKOfv4MBAJowvE5AOQOSrYYvyp/U+u4TkBO53oqZauukLE6UlcyuqbxiAd7dynkBDnQ3mPz2SZMkEvof9Qz0DGUvX4otnswbe/cnDj3a9vyPlNfB/iJv07kWdnrICVfTzvDE0R6vn+pOx4JQrckpSoj4yulptjVV4f8uGs9qUAT9jBYBzCqhbdKh+iJ6iYI4R8SWr8ZeU4u8CYHs367SI55m9H1dn7PTNYfZ1yC7U4G4zmyJmqNzgWkrLYYDBJdnlwBp/6y1lVTiH07O2favn8SmlOghnrIP5H/fFsVem
aws:
  automatically_update_role_trust_policies: false
celery:
  cache_cloudtrail_denies:
    enabled: true
  sync_regions:
    - us-east-1
    - us-west-2
policy_request_autoapprove_rules:
  enabled: true
  rules:
    - name: auto_approve_low_risk_s3
      description: |-
        This auto-approval rule automatically approves requests
        to pre-approved S3 buckets
      policy: |-
        {{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Action": [
                        "s3:getobject",
                        "s3:getobjectacl",
                        "s3:getobjecttagging",
                        "s3:getobjectversion",
                        "s3:getobjectversionacl",
                        "s3:getobjectversiontagging",
                        "s3:listbucket",
                        "s3:listbucketversions"
                    ],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::adostoma",
                        "arn:aws:s3:::adostoma/*",
                        "arn:aws:s3:::aenkvee",
                        "arn:aws:s3:::aenkvee/*"
                    ],
                    "Sid": "noquser1657458402wsng"
                }}
            ]
        }}
"""

cloudumi_saml_tenant_config = yaml.load(cloudumi_saml_config)
dict_merge(cloudumi_saml_tenant_config, tenant_secrets)
cloudumi_saml_config = yaml.dump(cloudumi_saml_tenant_config)
# Store cloudumisamldev information in DynamoDB

async_to_sync(ddb.update_static_config_for_tenant)(
    cloudumi_saml_config, override_email, "cloudumisamldev_com"
)


def create_tables():
    from common.scripts.alembic import run_alembic_migrations
    from common.scripts.initialize_postgres import rebuild_tables  # noqa: F401,E402

    try:
        run_alembic_migrations()
        asyncio.run(rebuild_tables())
        run_data_migrations()

    except Exception as e:
        print("Failed to create tables:", str(e))
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    p = multiprocessing.Process(target=create_tables)
    # Force rebuild SQL tables, deleting all existing data.
    p.start()
    p.join()

    if p.exitcode != 0:
        sys.exit(1)

    # ideompotent bootstrap per developer queue name
    region = config.get("_global_.integrations.aws.region", "us-west-2")
    account_id = config.get("_global_.integrations.aws.account_id")
    cluster_id = config.get("_global_.deployment.cluster_id")
    sqs_client = boto3.client("sqs", region_name=region)
    developer_queue_name = get_developer_queue_name()
    queue_arn = get_developer_queue_arn()
    try:
        _ = sqs_client.get_queue_url(
            QueueName=developer_queue_name,
        )
    except sqs_client.exceptions.QueueDoesNotExist:
        _ = sqs_client.create_queue(
            QueueName=developer_queue_name,
        )
    policy_json = allow_sns_to_write_to_sqs(
        GITHUB_APP_NOQ_DEV_WEBHOOK_SNS_ARN, queue_arn
    )

    response = sqs_client.get_queue_url(
        QueueName=developer_queue_name,
    )
    response = sqs_client.set_queue_attributes(
        QueueUrl=response["QueueUrl"], Attributes={"Policy": policy_json}
    )
    assert response
    # use a different block to ensure subscription to sns topic
    # SNS side seems to make sure it's idemopotent
    sns_client = boto3.client("sns", region_name=region)
    response = sns_client.subscribe(
        TopicArn=GITHUB_APP_NOQ_DEV_WEBHOOK_SNS_ARN,
        Protocol="sqs",
        Endpoint=queue_arn,
        ReturnSubscriptionArn=True,
    )
    assert response

    # bootstrap github app tenant association
    # If local dev overrides the GitHub ID,
    # they need to install their specific GitHub
    # to noqdev organization.
    if GITHUB_APP_ID == GITHUB_APP_ID_FOR_DEFAULT_LOCAL_DEV:
        local_tenants = ["localhost", "cloudumisamldev_com", "cloudumidev_com"]
        for local_tenant in local_tenants:
            db_tenant: Tenant = async_to_sync(Tenant.get_by_attr)("name", local_tenant)
            async_to_sync(GitHubInstall.create)(
                tenant=db_tenant, installation_id=DEV_IAMBIC_TEMPLATES_INSTALLATION_ID
            )

    # Force a re-cache of cloud resources with updated configuration
    import common.scripts.initialize_redis  # noqa: F401,E402
