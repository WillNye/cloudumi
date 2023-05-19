import os

TENANT_NAME = "localhost"
TENANT_API = "http://localhost:8092/api"
COOKIES = {
    "noq_auth": "YOUR_AUTH_COOKIE",
}


def setup():
    """
    Call this before importing ANYTHING in your QA tests.

    It will correctly set up your cloudumi config and environment variables.
    It will also load your DB models to prevent race conditions.
    """
    os.environ.setdefault(
        "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
    )
    os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

    from common.config import config  # noqa: F401,E402
