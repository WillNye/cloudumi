"""Docstring in public module."""
import os
import sys

import pytest

import common.lib.noq_json as json
from util.tests.fixtures.globals import tenant
from util.tests.fixtures.util import NOQAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
class TestUserProfile(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_profile(self):
        from common.config import config

        self.maxDiff = None
        headers = {
            config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@example.com",
            config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }

        response = self.fetch("/api/v2/user_profile", headers=headers)
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        response_j["site_config"].pop("noq_logo")
        self.assertEqual(
            response_j,
            {
                "site_config": {
                    "google_analytics": {"tracking_id": None, "options": {}},
                    "documentation_url": "/docs",
                    "support_contact": None,
                    "support_chat_url": "https://communityinviter.com/apps/noqcommunity/noq",
                    "security_logo": None,
                    "favicon": None,
                    "security_url": None,
                    "landing_url": None,
                    "notifications": {"enabled": None, "request_interval": 60},
                    "temp_policy_support": True,
                    "access": {"aws": {"default_region": "us-east-1"}},
                },
                "user": "testuser@example.com",
                "can_logout": True,
                "is_contractor": False,
                "mfa_setup_required": None,
                "mfa_verification_required": None,
                "needs_to_sign_eula": False,
                "password_reset_required": False,
                "employee_photo_url": "",
                "employee_info_url": "",
                "is_admin": False,
                "authorization": {
                    "can_edit_policies": False,
                    "can_create_roles": False,
                    "can_delete_iam_principals": False,
                },
                "pages": {
                    "header": {
                        "custom_header_message_title": "",
                        "custom_header_message_text": "",
                        "custom_header_message_route": ".*",
                    },
                    "role_login": {"enabled": True},
                    "groups": {"enabled": False},
                    "identity": {"enabled": False},
                    "users": {"enabled": False},
                    "policies": {"enabled": True},
                    "self_service": {"enabled": True},
                    "api_health": {"enabled": False},
                    "audit": {"enabled": False},
                    "config": {"enabled": False},
                },
                "accounts": {
                    "123456789012": "default_account_2",
                    "123456789013": "default_account_1",
                    "012345678901": "default_account_0",
                },
            },
        )
