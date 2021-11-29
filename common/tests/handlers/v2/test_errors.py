import ujson as json
from tests.globals import host
from tests.util import ConsoleMeAsyncHTTPTestCase


class TestNotFoundHandler(ConsoleMeAsyncHTTPTestCase):
    def get_app(self):
        from cloudumi_common.config import config

        self.config = config
        from cloudumi_api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        expected = {"status": 404, "title": "Not Found", "message": "Not Found"}
        headers = {
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.user_header_name", host
            ): "user@github.com",
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.groups_header_name", host
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/route_does_not_exist", method="GET", headers=headers
        )
        self.assertEqual(response.code, 404)
        self.assertDictEqual(json.loads(response.body), expected)

    def test_put(self):
        expected = {"status": 404, "title": "Not Found", "message": "Not Found"}
        headers = {
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.user_header_name", host
            ): "user@github.com",
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.groups_header_name", host
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/route_does_not_exist", method="PUT", headers=headers, body="{}"
        )
        self.assertEqual(response.code, 404)
        self.assertDictEqual(json.loads(response.body), expected)

    def test_post(self):
        expected = {"status": 404, "title": "Not Found", "message": "Not Found"}
        headers = {
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.user_header_name", host
            ): "user@github.com",
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.groups_header_name", host
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/route_does_not_exist", method="POST", headers=headers, body="{}"
        )
        self.assertEqual(response.code, 404)
        self.assertDictEqual(json.loads(response.body), expected)

    def test_patch(self):
        expected = {"status": 404, "title": "Not Found", "message": "Not Found"}
        headers = {
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.user_header_name", host
            ): "user@github.com",
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.groups_header_name", host
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/route_does_not_exist", method="PATCH", headers=headers, body="{}"
        )
        self.assertEqual(response.code, 404)
        self.assertDictEqual(json.loads(response.body), expected)

    def test_delete(self):
        expected = {"status": 404, "title": "Not Found", "message": "Not Found"}
        headers = {
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.user_header_name", host
            ): "user@github.com",
            self.config.get_host_specific_key(
                f"site_configs.{host}.auth.groups_header_name", host
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/route_does_not_exist", method="DELETE", headers=headers
        )
        self.assertEqual(response.code, 404)
        self.assertDictEqual(json.loads(response.body), expected)
