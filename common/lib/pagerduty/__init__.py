# WIP CODE FOR EVENTUAL PAGERDUTY INTEGRATION

from pdpyras import APISession

from common.config import config


class Pagerduty:
    def __init__(self, host):
        self.api_key = config.get_host_specific_key(
            f"site_configs.{host}.pagerduty_api_key", host
        )
        self.session = APISession(self.api_key)

    async def list_schedules(self):
        pass

    async def list_users(self):
        pass
