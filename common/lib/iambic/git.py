import datetime
import os
import time

from git import Repo
from git.exc import GitCommandError
from github import Github
from ruamel.yaml import YAML

from common.config import config
from common.lib.yaml import yaml


class IambicGit():
    def __init__(self, tenant: str) -> None:
        self.tenant: str = tenant
        self.global_repo_base_path: str = config.get("_global_.git.repo_base_path")
        self.git_repositories: dict[str, dict[str, str]] = config.get_tenant_specific_key("secrets.git.repositories", tenant, {})
        self.tenant_repo_base_path: str = os.path.expanduser(os.path.join(self.global_repo_base_path, tenant))
        os.makedirs(os.path.dirname(self.tenant_repo_base_path), exist_ok=True)
        self.repos = {}
        
    async def get_default_branch(self, repo) -> str:
        return next(ref for ref in repo.remotes.origin.refs if ref.name == "origin/HEAD").ref.name

    async def clone_or_pull_git_repos(self) -> None:
        # TODO: Formalize the model for secrets
        for repo_name, repository in self.git_repositories.items():
            git_uri = repository["uri"]
            # TODO: Enforce logical separation of tenant data
            repo_path = os.path.join(self.tenant_repo_base_path, repo_name)
            try:
                # TODO: async
                repo = Repo.clone_from(git_uri, repo_path)
                default_branch = await self.get_default_branch(repo)
                self.repos[repo_name] = {
                    "repo": repo, 
                    "path": repo_path, 
                    "gh": Github(repository["access_token"]),
                    "default_branch": default_branch
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
                repo.git.reset('--hard', default_branch)
                repo.git.pull()
                
                self.repos[repo_name] = {
                    "repo": repo, 
                    "path": repo_path, 
                    "gh": Github(repository["access_token"]),
                    "default_branch": default_branch
                    }
        return self.repos

    async def create_role_access_pr(self, role_arns: list[str], slack_user: str, duration: int, justification: str) -> None:
        errors = []
        await self.clone_or_pull_git_repos()
        # TODO: Need task to generate role_to_file_mapping
        role_to_file_mapping = {
            "arn:aws:iam::759357822767:role/demo_role_2":{"repo": "noq-templates", "path": "resources/aws/roles/demo_role_2.yaml"}
        }

        # TODO: Generate github username mapping
        slack_user_mapping = {
            "ccastrapel": {
                "github": "castrapel",
                "email": "curtis@noq.dev"
            },
            "steven": {
                "github": "smoy",
                "email": "steven@noq.dev"
            }
        }
        user = slack_user_mapping[slack_user]["email"]
        for role_arn in role_arns:
            account_id = role_arn.split(":")[4]
            if not role_to_file_mapping.get(role_arn):
                errors.append("We cannot find the requested role in git. Please contact your administrator.")
                continue
            repo_name = role_to_file_mapping[role_arn]["repo"]
            repo = self.repos[repo_name]
            template_path = os.path.join(self.tenant_repo_base_path, repo_name, role_to_file_mapping[role_arn]["path"])
            
            if not os.path.exists(template_path):
                errors.append("We cannot find the requested role template in git. Please contact your administrator.")
                continue

            template_dict = yaml.load(open(template_path))
            if not template_dict.get("role_access"):
                template_dict['role_access'] = []
            dt = datetime.datetime.now().astimezone()
            now = int(time.time())
            expires_at = dt + datetime.timedelta(seconds=int(duration))
            template_dict['role_access'].append({
                "users": [user],
                "included_accounts": [account_id],
                "expires_at": expires_at.isoformat()
                
            })
            as_yaml = yaml.dump(template_dict)
            with open(template_path, "w") as f:
                f.write(as_yaml)
            git = repo["repo"].git
            branch_name = f"{user.split('@')[0]}-{now}"
            git.checkout("HEAD", b=branch_name)
            git.add(template_path)
            git.commit("-m", f"Requesting role access for {user} to {role_arn} until {expires_at.isoformat()}\nJustification: {justification}")
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
        pr = gh_repo.create_pull(title=f"Access Request - {user} - {role_arns}", body=body, head=branch_name, base="main")
        return {
            "errors": errors,
            "github_pr": pr.html_url
        }
        
        
        
        
        