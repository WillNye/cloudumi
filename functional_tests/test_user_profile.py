import json

from functional_tests.conftest import (
    TEST_ACCOUNT_ID,
    TEST_ACCOUNT_NAME,
    TEST_USER_NAME,
    FunctionalTest,
)


class TestUserProfile(FunctionalTest):
    def test_user_profile(self):
        from common.config import config

        res = self.make_request("/api/v2/user_profile")
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)

        accounts = res_j.pop("accounts")

        self.assertIn(TEST_ACCOUNT_ID, accounts.keys())
        self.assertIn(TEST_ACCOUNT_NAME, accounts.values())

        self.assertEqual(
            res_j,
            {
                "site_config": {
                    "consoleme_logo": None,
                    "google_analytics": {
                        "tracking_id": config.get(
                            "_global_.google_analytics.tracking_id"
                        ),
                        "options": {},
                    },
                    "documentation_url": "/docs",
                    "support_contact": None,
                    "support_chat_url": "https://communityinviter.com/apps/noqcommunity/noq",
                    "security_logo": None,
                    "favicon": None,
                    "security_url": None,
                    "landing_url": None,
                    "notifications": {"enabled": True, "request_interval": 60},
                    "temp_policy_support": True,
                },
                "user": TEST_USER_NAME,
                "can_logout": True,
                "is_contractor": False,
                "employee_photo_url": "",
                "employee_info_url": "",
                "authorization": {
                    "can_edit_policies": True,
                    "can_create_roles": True,
                    "can_delete_iam_principals": True,
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
                    "config": {"enabled": True},
                },
            },
        )
