import time
from secrets import token_urlsafe

from asgiref.sync import async_to_sync

import common.scripts.initialize_dynamodb  # noqa: F401
from common.lib.dynamo import RestrictedDynamoHandler

tenant_config = f"""
_development_user_override: user@noq.dev
cloud_credential_authorization_mapping:
  role_tags:
    enabled: true
    authorized_groups_tags:
      - noq_authorized
    authorized_groups_cli_only_tags:
      - noq_authorized_cli
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
org_accounts:
  - org_id: test_org
    account_id: 123456789
    account_name: test_account
    owner: user
tenant_details:
  external_id: localhost
  creator: user@noq.dev
  creation_time: {int(time.time())}
site_config:
  landing_url: /
headers:
  identity:
    enabled: false
  role_login:
    enabled: true
url: https://localhost
application_admin: user@noq.dev
secrets:
  jwt_secret: {token_urlsafe(32)}
account_ids_to_name:
  "759357822767": "development"
"""

# Store tenant information in DynamoDB

ddb = RestrictedDynamoHandler()

async_to_sync(ddb.update_static_config_for_host)(
    tenant_config, "user@noq.dev", "localhost"
)

# Force a re-cache of cloud resources with updated configuration
import common.scripts.initialize_redis  # noqa: F401,E402
