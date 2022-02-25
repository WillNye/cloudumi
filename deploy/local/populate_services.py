import time
from secrets import token_urlsafe

from asgiref.sync import async_to_sync

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
  name: test_localhost
  account_id: 123456789
  role_arn: arn:aws:iam::123456789:role/aesenieg
  external_id: test_id
spoke_accounts:
  test_localhost_spoke__123456789:
    name: test_localhost_spoke
    account_id: 123456789
    role_arn: arn:aws:iam::123456789:role/aesenieg
    external_id: test_id
    hub_account_arn: arn:aws:iam::123456789:role/boss
    master_for_account: false
org_accounts:
  test_org:
    org_id: test_org
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
"""

# Store tenant information in DynamoDB

ddb = RestrictedDynamoHandler()

async_to_sync(ddb.update_static_config_for_host)(
    tenant_config, "user@noq.dev", "localhost"
)
