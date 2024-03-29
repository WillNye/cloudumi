import pytest

import common.lib.noq_json as json
from util.tests.fixtures.globals import tenant
from util.tests.fixtures.util import NOQAsyncHTTPTestCase


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestNotFoundHandler(NOQAsyncHTTPTestCase):
    def get_app(self):
        from common.config import config

        self.config = config
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        expected = {"status": 404, "title": "Not Found", "message": "Not Found"}
        headers = {
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
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
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
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
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
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
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
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
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/route_does_not_exist", method="DELETE", headers=headers
        )
        self.assertEqual(response.code, 404)
        self.assertDictEqual(json.loads(response.body), expected)
