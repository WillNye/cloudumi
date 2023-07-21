import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestTenantSummary:
    tenant: any
    tenant_name: Optional[str]
    tenant_url: Optional[str]
    username: Optional[str]
    user_groups: Optional[list[str]]
    cookies: Optional[dict[str, str]]

    def __init__(self):
        pass

    async def setup(
        self,
        tenant_name: str = "localhost",
        tenant_url: str = "http://localhost:8092",
        username: str = "user@noq.dev",
        user_groups: list[str] = None,
        **extra_cookies,
    ):
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
        from common.lib.jwt import generate_jwt_token
        from common.tenants.models import Tenant

        self.tenant = await Tenant.get_by_name(tenant_name)
        self.tenant_name = tenant_name
        self.tenant_url = tenant_url.replace("/api", "")
        self.username = username
        self.user_groups = user_groups or ["engineering@noq.dev"]
        self.cookies = {
            "noq_auth": await generate_jwt_token(
                self.username,
                self.user_groups,
                self.tenant_name,
                eula_signed=True,
                tenant_active=True,
            ),
            **extra_cookies,
        }


TENANT_SUMMARY = TestTenantSummary()
