from functional_tests.conftest import FunctionalTest


class TestDocs(FunctionalTest):
    def test_get_docs(self):
        headers = {"Content-Type": "text/html"}
        r = self.make_request("/docs/", method="get", headers=headers)

        self.assertEqual(r.code, 200)
