from secrets import token_urlsafe

from asgiref.sync import async_to_sync
import time

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

async_to_sync(ddb.update_static_config_for_host)(tenant_config, "user@noq.dev", "localhost")