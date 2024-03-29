from functional_tests.conftest import TEST_ROLE_ARN, FunctionalTest


class TestCredentials(FunctionalTest):
    def test_get_credentials(self):
        data = {"requested_role": TEST_ROLE_ARN}
        r = self.make_request("/api/v1/get_credentials", data, method="post")

        self.assertEqual(r.code, 200)
        self.assertIn(b"Credentials", r.body)
        self.assertIn(b"AccessKeyId", r.body)
        self.assertIn(b"SecretAccessKey", r.body)
        self.assertIn(b"SessionToken", r.body)
