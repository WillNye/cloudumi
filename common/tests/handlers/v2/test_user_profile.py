"""Docstring in public module."""
import os
import sys

import ujson as json
from tests.globals import host
from tests.util import ConsoleMeAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestUserProfile(ConsoleMeAsyncHTTPTestCase):
    def get_app(self):
        from cloudumi_api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_profile(self):
        from common.config import config

        self.maxDiff = None
        headers = {
            config.get_host_specific_key(
                f"site_configs.{host}.auth.user_header_name", host
            ): "user@example.com",
            config.get_host_specific_key(
                f"site_configs.{host}.auth.groups_header_name", host
            ): "groupa,groupb,groupc",
        }

        response = self.fetch("/api/v2/user_profile", headers=headers)
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        response_j["site_config"].pop("consoleme_logo")
        # self.assertIn("/images/logos/", consoleme_logo)
        self.assertEqual(
            response_j,
            {
                "site_config": {
                    "google_analytics": {"tracking_id": None, "options": {}},
                    "documentation_url": "https://hawkins.gitbook.io/consoleme/",
                    "support_contact": None,
                    "support_chat_url": "https://discord.com/invite/nQVpNGGkYu",
                    "security_logo": None,
                    "security_url": None,
                    "landing_url": None,
                    "notifications": {"enabled": None, "request_interval": 60},
                },
                "user": "testuser@example.com",
                "can_logout": False,
                "is_contractor": False,
                "employee_photo_url": "",
                "employee_info_url": "",
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
                    "groups": {"enabled": False},
                    "users": {"enabled": False},
                    "policies": {"enabled": True},
                    "self_service": {"enabled": True},
                    "api_health": {"enabled": False},
                    "audit": {"enabled": False},
                    "config": {"enabled": False},
                },
                "accounts": {"123456789012": "default_account"},
            },
        )
