from pathlib import Path

from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm.session import sessionmaker

from common.config import config

REDACTED_STR = "********"


class ClusterConfig:
    @property
    def dynamo_retry_count(self) -> int:
        return config.get("_global_.dynamo.retry_count", 10)

    @property
    def dynamo_wait_time_between_retries(self) -> int:
        return config.get("_global_.dynamo.wait_time_between_retries", 5)


TENANT_STORAGE_BASE_PATH = Path(
    config.get("_global_.tenant_storage.base_path", "/data/tenant_data/")
).expanduser()

ASYNC_PG_CONN_STR = f"postgresql+psycopg_async://{config.get('_global_.secrets.postgresql.username')}:{config.get('_global_.secrets.postgresql.password')}@{config.get('_global_.noq_db.endpoint')}:{config.get('_global_.noq_db.port')}/{config.get('_global_.noq_db.database')}"
ASYNC_PG_ENGINE = create_async_engine(ASYNC_PG_CONN_STR)
ASYNC_PG_SESSION = sessionmaker(
    ASYNC_PG_ENGINE,
    expire_on_commit=False,
    class_=AsyncSession,
)

AUTH_COOKIE_NAME: str = config.get("_global_.auth.cookie.name", "noq_auth")

ENVIRONMENT = config.get("_global_.environment")
IAMBIC_REPOS_BASE_KEY = "iambic_repos"
GITHUB_APP_URL = config.get("_global_.secrets.github_app.app_url")
assert GITHUB_APP_URL
if not GITHUB_APP_URL.endswith("/"):
    GITHUB_APP_URL = GITHUB_APP_URL + "/"
GITHUB_APP_ID = config.get("_global_.secrets.github_app.app_id")
assert GITHUB_APP_ID
GITHUB_APP_CLIENT_ID = config.get("_global_.secrets.github_app.client_id")
assert GITHUB_APP_CLIENT_ID
GITHUB_APP_CLIENT_SECRET = config.get("_global_.secrets.github_app.client_secret")
assert GITHUB_APP_CLIENT_SECRET
GITHUB_APP_PRIVATE_KEY = config.get("_global_.secrets.github_app.private_key")
assert GITHUB_APP_PRIVATE_KEY
GITHUB_APP_WEBHOOK_SECRET = config.get("_global_.secrets.github_app.webhook_secret")
assert GITHUB_APP_WEBHOOK_SECRET

SLACK_CLIENT_ID = config.get("_global_.secrets.slack.client_id")
assert SLACK_CLIENT_ID
SLACK_CLIENT_SECRET = config.get("_global_.secrets.slack.client_secret")
assert SLACK_CLIENT_SECRET
SLACK_SIGNING_SECRET = config.get("_global_.secrets.slack.signing_secret")
assert SLACK_SIGNING_SECRET
SLACK_BOT_TOKEN = config.get("_global_.secrets.slack.bot_token")
assert SLACK_BOT_TOKEN

SENDGRID_FROM_ADDRESS = config.get("_global_.secrets.sendgrid.from_address")
assert SENDGRID_FROM_ADDRESS

REDIS_PASSWORD = config.get("_global_.secrets.redis.password")
assert REDIS_PASSWORD

AWS_MARKETPLACE_SUBSCRIPTION_QUEUE = config.get(
    "_global_.integrations.aws.aws_marketplace_subscription_queue_arn"
)
if ENVIRONMENT == "prod":
    assert AWS_MARKETPLACE_SUBSCRIPTION_QUEUE
