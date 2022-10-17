from common.lib.dynamo import RestrictedDynamoHandler
from common.scripts.check_tenants import check_tenants
from functional_tests.conftest import FunctionalTest


class TestTenants(FunctionalTest):
    def test_all_tenants(self):
        ddb = RestrictedDynamoHandler()
        tenants = ddb.get_all_tenants()
        tenant_urls = []
        for tenant in tenants:
            tenant_config = ddb.get_static_config_for_tenant_sync(tenant)
            tenant_urls.append(tenant_config.get("url"))
        # tenant_urls = main()
        check_tenants(tenant_urls)
