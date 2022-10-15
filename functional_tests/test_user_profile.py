import json

from functional_tests.conftest import (
    TEST_ACCOUNT_ID,
    TEST_ACCOUNT_NAME,
    TEST_USER_NAME,
    FunctionalTest,
)


class TestUserProfile(FunctionalTest):
    def test_user_profile(self):
        res = self.make_request("/api/v2/user_profile")
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)

        accounts = res_j.pop("accounts")

        self.assertIn(TEST_ACCOUNT_ID, accounts.keys())
        self.assertIn(TEST_ACCOUNT_NAME, accounts.values())

        self.assertIn(
            "site_config",
            res_j,
        )
