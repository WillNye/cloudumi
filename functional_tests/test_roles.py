import json

from functional_tests.conftest import TEST_ROLE_ARN, FunctionalTest


class TestRoles(FunctionalTest):
    def test_eligible_roles(self):
        res = self.make_request(
            "/api/v2/eligible_roles?limit=1000",
            method="get",
        )
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        # User should have > 5 eligible roles
        self.assertIsInstance(res_j["data"], list)
        self.assertGreater(len(res_j["data"]), 5)

    def test_role_page_login_denied(self):
        res = self.make_request(
            "/api/v2/role_login/weirdinstanceprofile",
            follow_redirects=False,
            request_timeout=120,
        )
        self.assertEqual(res.code, 404)
        res_j = json.loads(res.body)
        self.assertEqual(
            res_j,
            {
                "type": "error",
                "message": "You do not have any roles matching your search criteria. ",
            },
        )

    def test_role_page_login(self):
        res = self.make_request(
            f"/api/v2/role_login/{TEST_ROLE_ARN}",
            follow_redirects=False,
            request_timeout=120,
        )
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        redirect_url = res_j.pop("redirect_url")
        self.assertIn(
            "https://signin.aws.amazon.com/federation?Action=login&",
            redirect_url,
        )
        self.assertEqual(
            res_j,
            {
                "type": "redirect",
                "reason": "console_login",
                "role": TEST_ROLE_ARN,
            },
        )

    def test_role_page_multiple(self):
        res = self.make_request("/api/v2/role_login/a", follow_redirects=False)
        res_j = json.loads(res.body)
        redirect_url = res_j.pop("redirect_url")
        self.assertIn("/?arn=a", redirect_url)
        self.assertEqual(
            res_j,
            {
                "type": "redirect",
                "message": "You have more than one role matching your query. Please select one.",
                "reason": "multiple_roles",
            },
        )
