import os

TENANT_NAME = "localhost"
TENANT_API = "http://localhost:8092/api"
TEST_USER_NAME = "user@noq.dev"
TEST_USER_GROUPS = ["engineering@noq.dev"]
COOKIES = {
    "noq_auth": "YOUR_AUTH_COOKIE",
}


async def setup():
    """
    Call this before importing ANYTHING in your QA tests.

    It will correctly set up your cloudumi config and environment variables.
    It will also load your DB models to prevent race conditions.
    """
    os.environ.setdefault(
        "CONFIG_LOCATION", "configs/development_account/local_saas_development.yaml"
    )
    os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

    from common.config import config  # noqa: F401,E402
    from common.lib.jwt import generate_jwt_token

    COOKIES["noq_auth"] = await generate_jwt_token(
        TEST_USER_NAME,
        TEST_USER_GROUPS,
        "localhost",
        eula_signed=True,
    )
