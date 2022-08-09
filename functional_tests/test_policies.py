import json

from functional_tests.conftest import FunctionalTest


class TestPolicies(FunctionalTest):
    def test_get_individual_role(self):
        res = self.make_request("/api/v2/roles/759357822767/NullRole")
        self.assertEqual(res.code, 200)
        self.assertIn(b"arn:aws:iam::759357822767:role/NullRole", res.body)
        res_j = json.loads(res.body)
        self.assertEqual(res_j["name"], "NullRole")
        self.assertEqual(res_j["account_id"], "759357822767")
        self.assertIn("arn", res_j.keys())
        self.assertIn("inline_policies", res_j.keys())
        self.assertIn("assume_role_policy_document", res_j.keys())
        self.assertIn("tags", res_j.keys())

    def test_standalone_self_service(self):
        res = self.make_request("/selfservice")
        self.assertEqual(res.code, 200)
        # TBD: How to test react?
        self.assertIn(b"favicon.ico", res.body)
