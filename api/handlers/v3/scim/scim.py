from common.handlers.base import TornadoRequestHandler


class SCIMIntegrationHandler(TornadoRequestHandler):
    async def prepare(self):
        print("here")
        self.tenant_config
        super(TornadoRequestHandler, self).prepare()

    async def get(self):
        """Get SCIM integration
        ---
        get:
            description: Get SCIM integration
            responses:
                200:
                    description: SCIM integration
        """
        self.write("OK")
