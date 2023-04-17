import json

from functional_tests.conftest import FunctionalTest


class TestSlack(FunctionalTest):
    def test_slack_get(self):
        res = self.make_request("/api/v3/slack/install")
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertTrue(
            (res_j["data"]["slack_install_url"]).startswith("https://slack.com")
        )
        res = self.make_request("/api/v3/slack")
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertEqual(res_j["data"]["installed"], True)

    def test_slack_delete(self):
        res = self.make_request("/api/v3/slack/install")
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertTrue(
            (res_j["data"]["slack_install_url"]).startswith("https://slack.com")
        )
        res = self.make_request("/api/v3/slack", method="DELETE")
        self.assertEqual(res.code, 200)
        res = self.make_request("/api/v3/slack")
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertEqual(res_j["data"]["installed"], False)
