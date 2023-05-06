import re
from typing import Optional

from pydantic import BaseModel

from common.handlers.base import BaseHandler
from common.iambic_request.request_crud import create_request, get_request_response
from common.lib.iambic.git import IambicGit
from common.models import IambicTemplateChange


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

    async def patch(self, path):
        # Ensure the request has the necessary JSON body
        if not self.request.body:
            self.set_status(400)
            self.write({"message": "Request body is required"})
            return

        # Parse the new YAML content from the request body
        try:
            new_yaml = self.request.json["raw_template_yaml"]
            justification = self.request.json.get(
                "justification", "No justification provided"
            )
        except KeyError:
            self.set_status(400)
            self.write({"message": "Request body must contain a 'yaml' field"})
            return

        # Reuse the existing path matching and file path candidates
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

        iambic_git = IambicGit(self.ctx.tenant)
        await iambic_git.set_git_repositories()

        # Check if the file exists and get the current file content
        real_file_path = None
        current_yaml = None
        for file_path in file_path_full_candidates:
            try:
                current_yaml = await iambic_git.get_raw_template_yaml(
                    full_repo_name, file_path
                )
            except Exception as e:
                if e.args[0] != "Template not found":
                    raise
            if current_yaml:
                real_file_path = file_path
                break

        if not real_file_path:
            self.set_status(404)
            self.write({"message": "Template not found"})
            return

        tenant = self.ctx.tenant
        created_by = self.user
        changes = [
            IambicTemplateChange(
                action="update",
                repo=full_repo_name,
                file_path=real_file_path,
                old_content=current_yaml,
                new_content=new_yaml,
            )
        ]

        request_result = await create_request(
            tenant, created_by, justification, changes, "WEB"
        )

        request = request_result["request"]

        # Get the pull request URL
        iambic_git = IambicGit(tenant)
        await iambic_git.set_git_repositories()
        request_pr = await iambic_git.get_pull_request_instance(
            full_repo_name, request.pull_request_id
        )
        response = await get_request_response(
            request, request_pr, include_comments=False
        )

        self.set_status(200)
        self.write(
            {
                "message": "Template updated and pull request created",
                "pull_request_url": response["html_url"],
            }
        )
