from common.handlers.base import BaseAPIV2Handler
from common.lib.templated_resources import retrieve_cached_resource_templates


class TemplatedResourceDetailHandler(BaseAPIV2Handler):
    async def get(self, repository_name, resource):

        tenant = self.ctx.tenant
        matching_template = await retrieve_cached_resource_templates(
            tenant,
            repository_name=repository_name,
            resource=resource,
            return_first_result=True,
        )
        if not matching_template:
            # TODO: Log here
            # Return 404
            self.write({})
            return
        self.write(matching_template.json())
