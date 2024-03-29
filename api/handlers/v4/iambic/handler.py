import re
from typing import Optional

from iambic.plugins.v0_1_0.aws.models import Description
from pydantic import BaseModel

from common.handlers.base import BaseHandler
from common.iambic.git.models import IambicRepo
from common.iambic.interface import IambicConfigInterface


class IAMbicTemplateInfo(BaseModel):
    last_updated: str
    external_link: str
    template_type: str
    description: Optional[str] = None
    identifier: Optional[str] = None
    raw_template_yaml: str
    file_path: str


class IambicResourcesHandler(BaseHandler):
    """Handler for /api/v4/resources/iambic endpoint"""

    async def get(self, path):
        match = re.match(r"([^/]+)/([^/]+)/(.+)", path)

        if not match:
            self.set_status(400)
            self.write({"message": "Invalid path"})
            return

        org_name, repo_name, file_path_partial = match.groups()
        full_repo_name = f"{org_name}/{repo_name}"
        file_path_full_candidates = [
            f"{file_path_partial}.yaml",
            f"{file_path_partial}.yml",
        ]
        iambic_repo = await IambicRepo.setup(self.ctx.db_tenant, full_repo_name)
        iambic_config = IambicConfigInterface(iambic_repo)
        templates = None
        real_file_path = None

        for file_path in file_path_full_candidates:
            try:
                templates = await iambic_config.retrieve_iambic_template(file_path)
            except Exception as e:
                if e.args[0] != "Template not found":
                    raise
            if templates:
                real_file_path = file_path
                break

        if not real_file_path:
            self.set_status(404)
            self.write({"message": "Template not found"})
            return

        template = templates[0]
        last_updated = await iambic_repo.get_last_updated(real_file_path)
        raw_template_yaml = await iambic_config.get_raw_template_yaml(real_file_path)
        template_info = IAMbicTemplateInfo(
            last_updated=last_updated,
            external_link=iambic_repo.generate_repo_link(real_file_path),
            template_type=template.template_type,
            description=self.get_template_description(template),
            identifier=getattr(template, "identifier", None),
            raw_template_yaml=raw_template_yaml,
            file_path=real_file_path,
        )

        self.write(template_info.dict())
        self.set_status(200)

    def get_template_description(self, template):
        template_description = getattr(template, "description", None)

        if not template_description:
            properties_description = getattr(
                template,
                "description",
                getattr(getattr(template, "properties"), "description", None),
            )

            if isinstance(properties_description, str):
                return properties_description

            if isinstance(properties_description, Description):
                return properties_description.description

            if isinstance(properties_description, list):
                return (
                    properties_description[0].description
                    if properties_description
                    else None
                )

        return template_description
