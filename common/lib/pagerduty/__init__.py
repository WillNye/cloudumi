# WIP CODE FOR EVENTUAL PAGERDUTY INTEGRATION

from pdpyras import APISession

from common.config import config


class Pagerduty:
    def __init__(self, tenant):
        self.api_key = config.get_tenant_specific_key("pagerduty_api_key", tenant)
        self.session = APISession(self.api_key)

    async def list_schedules(self):
        pass

    async def list_users(self):
        pass
