from common.handlers.base import BaseAPIV2Handler
from common.lib.terraform import retrieve_cached_terraform_resources


class TerraformResourceDetailHandler(BaseAPIV2Handler):
    async def get(self, repository_name, resource):

        host = self.ctx.host
        matching_resource = await retrieve_cached_terraform_resources(
            host,
            repository_name=repository_name,
            resource=resource,
            return_first_result=True,
        )
        if not matching_resource:
            # TODO: Log here
            # Return 404
            self.write({})
            return
        self.write(matching_resource.json())
