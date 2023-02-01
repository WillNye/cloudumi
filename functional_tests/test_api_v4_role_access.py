import json

from functional_tests.conftest import FunctionalTest


class TestApiV4RoleAccess(FunctionalTest):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_retrieve_items(self):
        body = {}
        res = self.make_request("/api/v4/roles/access", method="post", body=body)
        print(res.body)
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertIn("data", res_j.keys())
        data = res_j.get("data")
        self.assertIn("access_roles", data)
        access_roles = data.get("access_roles")
        self.assertGreater(len(access_roles), 0)

    def test_filter_retrieve_items(self):
        body = {
            "filter": {
                "pagination": {"currentPageIndex": 1, "pageSize": 30},
                "sorting": {
                    "sortingColumn": {
                        "id": "id",
                        "sortingField": "id",
                        "header": "id",
                        "minWidth": 180,
                    },
                    "sortingDescending": False,
                },
                "filtering": {
                    "tokens": [
                        {
                            "propertyKey": "user.email",
                            "operator": "=",
                            "value": "admin_user@noq.dev",
                        }
                    ],
                    "operation": "and",
                },
            }
        }
        res = self.make_request("/api/v4/roles/access", method="post", body=body)
        print(res.body)
        self.assertEqual(res.code, 200)
        res_j = json.loads(res.body)
        self.assertIn("data", res_j.keys())
        data = res_j.get("data")
        self.assertIn("access_roles", data)
        access_roles = data.get("access_roles")
        self.assertGreater(len(access_roles), 0)

    def test_filter_not_found_returns_500(self):
        body = {
            "filter": {
                "pagination": {"currentPageIndex": 1, "pageSize": 30},
                "sorting": {
                    "sortingColumn": {
                        "id": "id",
                        "sortingField": "id",
                        "header": "id",
                        "minWidth": 180,
                    },
                    "sortingDescending": False,
                },
                "filtering": {
                    "tokens": [
                        {
                            "propertyKey": "user.email",
                            "operator": "=",
                            "value": "not_exists@noq.dev",
                        }
                    ],
                    "operation": "and",
                },
            }
        }
        res = self.make_request("/api/v4/roles/access", method="post", body=body)
        print(res.body)
        self.assertEqual(res.code, 500)
