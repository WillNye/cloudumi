import os
import time
from secrets import token_urlsafe

from asgiref.sync import async_to_sync

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "noq_cluster_dev")
override_email = os.getenv("OVERRIDE_EMAIL", "user@noq.dev")

import common.scripts.initialize_dynamodb  # noqa: F401, E402
from common.lib.dynamo import RestrictedDynamoHandler  # noqa: F401, E402

tenant_config = f"""
_development_user_override: {override_email}
_development_groups_override:
  - engineering@noq.dev
  - {override_email}
notifications:
  enabled: true
cloudtrail:
  enabled: true
  account_id: "759357822767"
  queue_arn: arn:aws:sqs:us-west-2:759357822767:noq-cloudtrail-access-denies
cache_self_service_typeahead:
  cache_resource_templates: true
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
    master_for_account: false
  - name: NoqSpokeRoleLocalDev
    account_name: development_2
    account_id: '350876197038'
    role_arn: arn:aws:iam::350876197038:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    master_for_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
org_accounts:
  - org_id: test_org
    account_id: '759357822767'
    account_name: test_account
    owner: user
tenant_details:
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
  creator: {override_email}
  creation_time: {int(time.time())}
site_config:
  landing_url: /
  notifications: enabled
  request_interval: 1
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
url: https://localhost
application_admin: engineering@noq.dev
secrets:
  jwt_secret: {token_urlsafe(32)}
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
account_ids_to_name:
  "759357822767": "development"
celery:
  cache_cloudtrail_denies:
    enabled: true
"""

# Store tenant information in DynamoDB

ddb = RestrictedDynamoHandler()

async_to_sync(ddb.update_static_config_for_host)(
    tenant_config, override_email, "localhost"
)

cloudumi_config = f"""
_development_user_override: {override_email}
_development_groups_override:
  - engineering@noq.dev
  - {override_email}
cache_self_service_typeahead:
  cache_resource_templates: true
notifications:
  enabled: true
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
spoke_accounts:
  - name: NoqSpokeRoleLocalDev
    account_name: 'development'
    account_id: '759357822767'
    role_arn: arn:aws:iam::759357822767:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    master_for_account: false
  - name: NoqSpokeRoleLocalDev
    account_name: development_2
    account_id: '350876197038'
    role_arn: arn:aws:iam::350876197038:role/NoqSpokeRoleLocalDev
    external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
    hub_account_arn: arn:aws:iam::759357822767:role/NoqCentralRoleLocalDev
    master_for_account: false
    owners: []
    viewers: []
    delegate_admin_to_owner: false
    restrict_viewers_of_account_resources: false
org_accounts:
  - org_id: test_org
    account_id: '759357822767'
    account_name: test_account
    owner: user
tenant_details:
  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43
  creator: {override_email}
  creation_time: {int(time.time())}
site_config:
  landing_url: /
  notifications: enabled
  request_interval: 1
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
url: https://cloudumidev.com
application_admin: engineering@noq.dev
secrets:
  jwt_secret: {token_urlsafe(32)}
  auth:
    oidc:
      client_id: 'j14h62of81s6s5f2ivfkdfe3v'
      client_secret: '1l4g523pb7rb3iicm9jod80nlst3r92f4oitg2dijna45pegj4dh'
  cognito:
    config:
      user_pool_id: 'us-east-1_CNoZribID'
      user_pool_client_id: 'j14h62of81s6s5f2ivfkdfe3v'
      user_pool_client_secret: '1l4g523pb7rb3iicm9jod80nlst3r92f4oitg2dijna45pegj4dh'
      user_pool_region: 'us-east-1'
account_ids_to_name:
  "759357822767": "development"
auth:
  challenge_url:
    enabled: true
  get_user_by_oidc: true
get_user_by_oidc_settings:
  client_scopes:
    - email
    - openid
  resource: noq_tenant
  metadata_url: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_CNoZribID/.well-known/openid-configuration
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
"""

# Store cloudumidev information in DynamoDB

ddb = RestrictedDynamoHandler()

async_to_sync(ddb.update_static_config_for_host)(
    cloudumi_config, override_email, "cloudumidev_com"
)

# Force a re-cache of cloud resources with updated configuration
import common.scripts.initialize_redis  # noqa: F401,E402
