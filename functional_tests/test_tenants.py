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
            if type(tenant_config) == dict:
                # There seems to be an issue when a tenant does not have
                # a master version, and get_all_tenants will include
                # it and the subsequent get config will fail.
                tenant_urls.append(tenant_config.get("url"))
        check_tenants(tenant_urls)
