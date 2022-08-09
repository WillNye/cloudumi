from functional_tests.conftest import FunctionalTest


class TestDocs(FunctionalTest):
    def test_get_docs(self):
        r = self.make_request("/docs", method="get")

        self.assertEqual(r.code, 200)
