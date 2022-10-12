from common.scripts.check_tenants import check_tenants
from common.scripts.dump_tenants import main
from functional_tests.conftest import FunctionalTest


class TestTenants(FunctionalTest):
    def test_all_tenants(self):
        tenant_urls = main()
        check_tenants(tenant_urls)
