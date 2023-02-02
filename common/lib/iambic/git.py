import datetime
import os
import time

import ujson as json
from git import Repo
from git.exc import GitCommandError
from github import Github
from iambic.core.parser import load_templates

# TODO: Still need to get Iambic installed in the SaaS. This is a localhost hack.
from iambic.core.utils import gather_templates
from iambic.google.group.models import GroupMember
from ruamel.yaml import YAML

from common.config import config, models
from common.config.globals import TENANT_STORAGE_BASE_PATH
from common.lib.cache import store_json_results_in_redis_and_s3
from common.lib.yaml import yaml
from common.models import IambicRepoDetails

IAMBIC_REPOS_BASE_KEY = "iambic_repos"


def get_iambic_repo_path(tenant, repo_name):
    return os.path.join(
        TENANT_STORAGE_BASE_PATH, f"{tenant}/iambic_template_repos/{repo_name}"
    )


class IambicGit:
    def __init__(self, tenant: str) -> None:
        self.tenant: str = tenant
        self.git_repositories = []
        self.tenant_repo_base_path: str = os.path.expanduser(
            os.path.join(TENANT_STORAGE_BASE_PATH, tenant)
        )
        os.makedirs(os.path.dirname(self.tenant_repo_base_path), exist_ok=True)
        self.repos = {}

    async def set_git_repositories(self) -> None:
        self.git_repositories: list[IambicRepoDetails] = (
            models.ModelAdapter(IambicRepoDetails)
            .load_config(IAMBIC_REPOS_BASE_KEY, self.tenant)
            .models
        )

    async def get_default_branch(self, repo) -> str:
        return next(
            ref for ref in repo.remotes.origin.refs if ref.name == "origin/HEAD"
        ).ref.name

    async def clone_or_pull_git_repos(self) -> None:
        # TODO: Formalize the model for secrets
        await self.set_git_repositories()
        for repository in self.git_repositories:
            repo_name = repository.repo_name
            access_token = repository.access_token
            repo_path = get_iambic_repo_path(self.tenant, repository.repo_name)
            git_uri = f"https://oauth:{access_token}@github.com/{repo_name}"
            try:
                # TODO: async
                repo = Repo.clone_from(
                    git_uri,
                    repo_path,
                    config="core.symlinks=false",
                )
                default_branch = await self.get_default_branch(repo)
                self.repos[repo_name] = {
                    "repo": repo,
                    "path": repo_path,
                    "gh": Github(repository.access_token),
                    "default_branch": default_branch,
                }
            except GitCommandError as e:
                if "already exists and is not an empty directory" not in e.stderr:
                    raise
                # TODO: async
                repo = Repo(repo_path)
                for remote in repo.remotes:
                    remote.fetch()
                default_branch = await self.get_default_branch(repo)
                default_branch_name = default_branch.split("/")[-1]
                repo.git.checkout(default_branch_name)
                repo.git.reset("--hard", default_branch)
                repo.git.pull()

                self.repos[repo_name] = {
                    "repo": repo,
                    "path": repo_path,
                    "gh": Github(repository.access_token),
                    "default_branch": default_branch,
                }
        return

    async def gather_templates_for_tenant(self):
        await self.set_git_repositories()
        for repository in self.git_repositories:
            repo_name = repository.repo_name
            repo_path = os.path.join(self.tenant_repo_base_path, repo_name)
            template_paths = await gather_templates(repo_path)
            self.templates = load_templates(template_paths)
            group_typeahead = []
            template_dicts = []
            for template in self.templates:
                d = json.loads(template.json())
                d["repo_name"] = repo_name
                d["file_path"] = d["file_path"].replace(self.tenant_repo_base_path, "")
                d["repo_relative_file_path"] = d["file_path"].replace(
                    "/" + repo_name, ""
                )
                template_dicts.append(d)
            # jmespath.search("[?template_type=='NOQ::Google::Group' && contains(properties.name, 'leg')]", template_dicts)
            redis_key = config.get_tenant_specific_key(
                "cache_organization_structure.redis.key.org_structure_key",
                self.tenant,
                f"{self.tenant}_IAMBIC_TEMPLATES",
            )
            await store_json_results_in_redis_and_s3(
                template_dicts,
                redis_key=redis_key,
                tenant=self.tenant,
            )
            for template in self.templates:
                if template.template_type in ["NOQ::Google::Group"]:
                    group_typeahead.append(
                        {
                            "name": "aws_org2_audit_account@noq.dev",
                        }
                    )

            # Cache Group typeahead
            # Cache Role ARN Typeahead

    async def cache_okta_groups_for_tenant(self, tenant, groups=None) -> list[str]:
        okta_groups = []
        for repo_name, repo in self.repos.items():
            if repo_name == "noq-templates":
                okta_groups.append("noq-templates")
                continue
            okta_groups.append(repo_name)
        return okta_groups

    async def request_access_to_groups(
        self, groups: list[str], slack_user: str, duration: int, justification: str
    ) -> None:
        errors = []
        await self.clone_or_pull_git_repos()

    async def retrieve_iambic_template(self, repo_name: str, template_path: str):
        await self.set_git_repositories()
        for repository in self.git_repositories:
            if not repository.repo_name == repo_name:
                continue
            full_path = os.path.join(
                self.tenant_repo_base_path, repo_name, template_path
            )
            if not os.path.exists(full_path):
                continue
            return load_templates([full_path])
        raise Exception("Template not found")

    async def google_add_user_to_group(
        self,
        template_type: str,
        repo_name: str,
        file_path: str,
        user_email: str,
        duration: int,
    ) -> None:
        await self.clone_or_pull_git_repos()
        errors = []
        if template_type != "NOQ::Google::Group":
            raise Exception("Template type is not a Google Group")
        templates = await self.retrieve_iambic_template(repo_name, file_path)
        if not templates:
            raise Exception("Template not found")
        template = templates[0]
        if template.template_type != template_type:
            raise Exception("Template type does not match")
        expires_at = None
        group_member = GroupMember(
            email=user_email,
            expires_at=expires_at,
        )
        if duration and duration != "no_expire":
            group_member.expires_at = f"in {duration} seconds"

        template.properties.members.append(group_member)
        return template

    async def create_role_access_pr(
        self, role_arns: list[str], slack_user: str, duration: int, justification: str
    ) -> None:
        errors = []
        await self.clone_or_pull_git_repos()
        # TODO: Need task to generate role_to_file_mapping
        role_to_file_mapping = {
            "arn:aws:iam::759357822767:role/demo_role_2": {
                "repo": "noq-templates",
                "path": "resources/aws/roles/demo_role_2.yaml",
            }
        }

        # TODO: Generate github username mapping
        slack_user_mapping = {
            "ccastrapel": {"github": "castrapel", "email": "curtis@noq.dev"},
            "steven": {"github": "smoy", "email": "steven@noq.dev"},
        }
        user = slack_user_mapping[slack_user]["email"]
        for role_arn in role_arns:
            account_id = role_arn.split(":")[4]
            if not role_to_file_mapping.get(role_arn):
                errors.append(
                    "We cannot find the requested role in git. Please contact your administrator."
                )
                continue
            repo_name = role_to_file_mapping[role_arn]["repo"]
            repo = self.repos[repo_name]
            template_path = os.path.join(
                self.tenant_repo_base_path,
                repo_name,
                role_to_file_mapping[role_arn]["path"],
            )

            if not os.path.exists(template_path):
                errors.append(
                    "We cannot find the requested role template in git. Please contact your administrator."
                )
                continue

            template_dict = yaml.load(open(template_path))
            if not template_dict.get("role_access"):
                template_dict["role_access"] = []
            dt = datetime.datetime.now().astimezone()
            now = int(time.time())
            expires_at = dt + datetime.timedelta(seconds=int(duration))
            template_dict["role_access"].append(
                {
                    "users": [user],
                    "included_accounts": [account_id],
                    "expires_at": expires_at.isoformat(),
                }
            )
            as_yaml = yaml.dump(template_dict)
            with open(template_path, "w") as f:
                f.write(as_yaml)
            git = repo["repo"].git
            branch_name = f"{user.split('@')[0]}-{now}"
            git.checkout("HEAD", b=branch_name)
            git.add(template_path)
            git.commit(
                "-m",
                f"Requesting role access for {user} to {role_arn} until {expires_at.isoformat()}\nJustification: {justification}",
            )
            git.push("--set-upstream", "origin", branch_name)
        gh = repo["gh"]
        # TODO hardcoded
        role_arns = ", ".join(role_arns)
        gh_repo = gh.get_repo(f"noqdev/noq-templates")
        body = f"""
Access Request Detail:

:small_blue_diamond: **User**: {user}
:small_blue_diamond: **Cloud Identities**: {role_arns}
:small_blue_diamond: **Justification**: {justification}
        """
        # TODO: Figure out base branch
        # gh_repo.get_branch(branch=branch_name)
        pr = gh_repo.create_pull(
            title=f"Access Request - {user} - {role_arns}",
            body=body,
            head=branch_name,
            base="main",
        )
        return {"errors": errors, "github_pr": pr.html_url}
