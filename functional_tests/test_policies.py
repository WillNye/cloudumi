import json

from functional_tests.conftest import (
    TEST_ACCOUNT_ID,
    TEST_ROLE,
    TEST_ROLE_ARN,
    FunctionalTest,
)


class TestPolicies(FunctionalTest):
    def test_get_individual_role(self):
        res = self.make_request(f"/api/v2/roles/{TEST_ACCOUNT_ID}/{TEST_ROLE}")
        self.assertEqual(res.code, 200)
        self.assertIn(f"{TEST_ROLE_ARN}".encode(), res.body)
        res_j = json.loads(res.body)
        self.assertEqual(res_j["name"], "NullRole")
        self.assertEqual(res_j["account_id"], TEST_ACCOUNT_ID)
        self.assertIn("arn", res_j.keys())
        self.assertIn("inline_policies", res_j.keys())
        self.assertIn("assume_role_policy_document", res_j.keys())
        self.assertIn("tags", res_j.keys())

    def test_standalone_self_service(self):
        res = self.make_request("/selfservice")
        self.assertEqual(res.code, 200)
        # TBD: How to test react?
        self.assertIn(b"favicon.ico", res.body)
