import re
from typing import Optional

from pydantic import BaseModel

from common.handlers.base import BaseHandler
from common.lib.iambic.git import IambicGit


class IAMbicTemplateInfo(BaseModel):
    last_updated: str
    external_link: str
    template_type: str
    description: Optional[str] = None
    identifier: Optional[str] = None
    raw_template_yaml: str
    file_path: str


class IambicResourcesHandler(BaseHandler):
    async def get(self, path):
        match = re.match(r"([^/]+)/([^/]+)/(.+)", path)

        if not match:
            self.set_status(400)
            self.write({"message": "Invalid path"})
            return

        org_name, repo_name, file_path_partial = match.groups()
        full_repo_name = f"{org_name}/{repo_name}"
        file_path_full_canddiates = [
            f"{file_path_partial}.yaml",
            f"{file_path_partial}.yml",
        ]

        iambic_git = IambicGit(self.ctx.tenant)
        await iambic_git.set_git_repositories()

        templates = None

        real_file_path = None

        for file_path in file_path_full_canddiates:
            try:
                templates = await iambic_git.retrieve_iambic_template(
                    full_repo_name, file_path
                )
            except Exception as e:
                if e.args[0] != "Template not found":
                    raise
            if templates:
                real_file_path = file_path
                break

        if not templates:
            self.set_status(404)
            self.write({"message": "Template not found"})
            return

        template = templates[0]
        last_updated = await iambic_git.get_last_updated(full_repo_name, file_path)
        raw_template_yaml = await iambic_git.get_raw_template_yaml(
            full_repo_name, file_path
        )

        # TODO: hack alert with `main` hardcoded
        github_link = await iambic_git.generate_github_link(
            org_name, repo_name, "main", real_file_path
        )
        template_info = IAMbicTemplateInfo(
            last_updated=last_updated,
            external_link=github_link,
            template_type=template.template_type,
            description=getattr(template, "description", None),
            identifier=getattr(template, "identifier", None),
            raw_template_yaml=raw_template_yaml,
            file_path=real_file_path,
        )

        self.write(template_info.dict())
        self.set_status(200)
