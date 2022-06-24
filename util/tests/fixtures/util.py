from asgiref.sync import async_to_sync
from tornado.testing import AsyncHTTPTestCase

from util.tests.fixtures.globals import tenant, tenant_header


def generate_jwt_token_for_testing(
    user="testuser@example.com", groups=None, formatted_tenant_name=tenant
):
    from common.lib.jwt import generate_jwt_token

    if not groups:
        groups = ["groupa", "groupb", "groupc"]
    if isinstance(groups, str):
        groups = groups.split(",")
    return async_to_sync(generate_jwt_token)(user, groups, formatted_tenant_name)


class ConsoleMeAsyncHTTPTestCase(AsyncHTTPTestCase):
    def __init__(self, *args, **kwargs):
        self.maxDiff = None
        super(ConsoleMeAsyncHTTPTestCase, self).__init__(*args, **kwargs)

    def fetch(self, *args, **kwargs):
        user = kwargs.pop("user", "testuser@example.com")
        groups = kwargs.pop("groups", None)
        omit_headers = kwargs.pop("omit_headers", False)
        if not omit_headers:
            headers = kwargs.pop("headers", {})
            headers["host"] = tenant_header
            if not headers.get("Cookie"):
                headers["Cookie"] = "=".join(
                    (
                        "noq_auth",
                        generate_jwt_token_for_testing(user=user, groups=groups),
                    )
                )
            kwargs["headers"] = headers
        return super(ConsoleMeAsyncHTTPTestCase, self).fetch(*args, **kwargs)

    def fetch_mutual_tls(self, *args, **kwargs):
        omit_headers = kwargs.pop("omit_headers", False)
        if not omit_headers:
            headers = kwargs.pop("headers", {})
            headers["host"] = tenant_header
            if not headers.get("Cookie"):
                headers["Cookie"] = "=".join(
                    ("noq_auth", generate_jwt_token_for_testing())
                )
            kwargs["headers"] = headers
        return super(ConsoleMeAsyncHTTPTestCase, self).fetch(*args, **kwargs)
