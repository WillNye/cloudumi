import datetime
import hashlib
import os
import time
from typing import Optional, Union

import ujson as json
from git import Repo
from git.exc import GitCommandError
from github import Github
from iambic.config.dynamic_config import load_config as load_config_template
from iambic.config.utils import resolve_config_template_path
from iambic.core.models import BaseTemplate
from iambic.core.parser import load_templates

# TODO: Still need to get Iambic installed in the SaaS. This is a localhost hack.
from iambic.core.utils import gather_templates
from iambic.plugins.v0_1_0.aws.iam.policy.models import PolicyDocument, PolicyStatement
from iambic.plugins.v0_1_0.google.group.models import GroupMember
from iambic.plugins.v0_1_0.okta.group.models import UserSimple
from iambic.plugins.v0_1_0.okta.models import Assignment
from jinja2.environment import Environment
from jinja2.loaders import BaseLoader

from common.config import models
from common.config.globals import TENANT_STORAGE_BASE_PATH
from common.config.tenant_config import TenantConfig
from common.lib.cache import store_json_results_in_redis_and_s3
from common.lib.iambic.util import effective_accounts
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
            os.path.join(TENANT_STORAGE_BASE_PATH, tenant, "iambic_template_repos")
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
        tenant_config = TenantConfig(self.tenant)
        await self.set_git_repositories()
        for repository in self.git_repositories:
            repo_name = repository.repo_name
            repo_path = get_iambic_repo_path(self.tenant, repository.repo_name)
            config_template_path = await resolve_config_template_path(repo_path)
            # TODO: Need to have assume role access and ability to read secret
            # for Iambic config and templates to load
            config_template = await load_config_template(
                config_template_path, sparse=True
            )
            template_paths = await gather_templates(repo_path)
            self.templates = load_templates(template_paths)
            group_typeahead = []
            template_dicts = []

            aws_account_specific_template_types = {
                "NOQ::AWS::IAM::Role",
                "NOQ::AWS::IAM::Group",
                "NOQ::AWS::IAM::ManagedPolicy",
                "NOQ::AWS::IAM::User",
            }
            aws_accounts = config_template.aws.accounts
            aws_account_dicts = []
            account_ids_to_account_names = {}
            for aws_account in aws_accounts:
                d = json.loads(aws_account.json())
                d["repo_name"] = repo_name
                aws_account_dicts.append(d)
                account_ids_to_account_names[
                    aws_account.account_id
                ] = aws_account.account_name

            await store_json_results_in_redis_and_s3(
                aws_account_dicts,
                redis_key=tenant_config.iambic_aws_accounts,
                tenant=self.tenant,
            )
            from iambic.core.utils import evaluate_on_provider

            arn_typeahead = {}
            reverse_hash = {}
            reverse_hash_for_templates = {}
            for template in self.templates:
                arns = []
                if template.template_type in aws_account_specific_template_types:
                    for account in aws_accounts:
                        variables = {
                            var.key: var.value for var in aws_account.variables
                        }
                        variables["account_id"] = aws_account.account_id
                        variables["account_name"] = aws_account.account_name
                        if hasattr(template, "owner") and (
                            owner := getattr(template, "owner", None)
                        ):
                            variables["owner"] = owner
                        # included = await is_included_in_account(account_id, account_name, included_accounts, excluded_accounts)
                        included = evaluate_on_provider(template, account, None)
                        if included:
                            arn = None
                            # calculate arn
                            if template.template_type == "NOQ::AWS::IAM::Role":
                                arn = f"arn:aws:iam::{account.account_id}:role{template.properties.path}{template.properties.role_name}"
                            elif template.template_type == "NOQ::AWS::IAM::Group":
                                arn = f"arn:aws:iam::{account.account_id}:group{template.properties.path}{template.properties.group_name}"
                            elif (
                                template.template_type == "NOQ::AWS::IAM::ManagedPolicy"
                            ):
                                arn = f"arn:aws:iam::{account.account_id}:policy{template.properties.path}{template.properties.policy_name}"
                            elif template.template_type == "NOQ::AWS::IAM::User":
                                arn = f"arn:aws:iam::{account.account_id}:user{template.properties.path}{template.properties.user_name}"
                            else:
                                raise Exception(
                                    f"Unsupported template type: {template.template_type}"
                                )
                            if arn:
                                rtemplate = Environment(
                                    loader=BaseLoader()
                                ).from_string(arn)
                                arn = rtemplate.render(**variables)
                                arns.append(arn)
                    pass
                d = json.loads(template.json())
                if arns:
                    d["arns"] = arns
                d["repo_name"] = repo_name
                d["file_path"] = d["file_path"].replace(self.tenant_repo_base_path, "")
                d["repo_relative_file_path"] = d["file_path"].replace(
                    "/" + repo_name, ""
                )
                d["hash"] = hashlib.md5(d["file_path"].encode("utf-8")).hexdigest()
                reverse_hash_for_templates[d["hash"]] = d
                if d["repo_relative_file_path"].startswith("/"):
                    d["repo_relative_file_path"] = d["repo_relative_file_path"][1:]
                template_dicts.append(d)
                for arn in arns:
                    if (
                        ":role/aws-service-role/" in arn
                        or ":role/aws-reserved/sso.amazonaws.com/" in arn
                        or ":role/stacksets-exec-" in arn
                        or ":role/OrganizationAccountAccessRole" in arn
                        or ":role/service-role/" in arn
                        or ":role/cdk-" in arn
                        or ":role/mciem-collection-role" in arn
                    ):
                        continue
                    # Short hack to quickly identify the value
                    reverse_hash_for_arn = hashlib.md5(arn.encode("utf-8")).hexdigest()
                    account_id = arn.split(":")[4]
                    arn_typeahead[arn] = {
                        "account_name": account_ids_to_account_names.get(account_id),
                        "template_type": d["template_type"],
                        "repo_name": d["repo_name"],
                        "file_path": d["file_path"],
                        "repo_relative_file_path": d["repo_relative_file_path"],
                        "hash": reverse_hash_for_arn,
                    }
                    reverse_hash[reverse_hash_for_arn] = {
                        "arn": arn,
                        "template_type": d["template_type"],
                        "repo_name": d["repo_name"],
                        "file_path": d["file_path"],
                        "repo_relative_file_path": d["repo_relative_file_path"],
                    }

            # iambic_template_rules = await get_data_for_template_types(self.tenant, aws_account_specific_template_types)
            # jmespath.search("[?template_type=='NOQ::Google::Group' && contains(properties.name, 'leg')]", template_dicts)
            await store_json_results_in_redis_and_s3(
                template_dicts,
                redis_key=tenant_config.iambic_templates_redis_key,
                tenant=self.tenant,
            )
            await store_json_results_in_redis_and_s3(
                reverse_hash_for_templates,
                redis_key=tenant_config.iambic_templates_reverse_hash_redis_key,
                tenant=self.tenant,
            )

            await store_json_results_in_redis_and_s3(
                arn_typeahead,
                redis_key=tenant_config.iambic_arn_typeahead_redis_key,
                tenant=self.tenant,
            )
            await store_json_results_in_redis_and_s3(
                reverse_hash,
                redis_key=tenant_config.iambic_hash_arn_redis_key,
                tenant=self.tenant,
            )

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
        # await self.clone_or_pull_git_repos()

    async def retrieve_iambic_template(self, repo_name: str, template_path: str):
        await self.set_git_repositories()
        for repository in self.git_repositories:
            # TODO: Need to have assume role access and ability to read secret
            # for Iambic config and templates to load
            if not repository.repo_name == repo_name:
                continue
            repo_path = os.path.join(self.tenant_repo_base_path, repo_name)
            full_path = os.path.join(repo_path, template_path)
            if not os.path.exists(full_path):
                continue
            config_template_path = await resolve_config_template_path(repo_path)
            config_template = await load_config_template(
                config_template_path, sparse=True
            )
            return load_templates([full_path])
        raise Exception("Template not found")

    async def okta_add_user_to_app(
        self,
        template_type: str,
        repo_name: str,
        file_path: str,
        user_email: str,
        duration: int,
    ):
        # await self.clone_or_pull_git_repos()
        if template_type != "NOQ::Okta::App":
            raise Exception("Template type is not a Okta App")
        templates = await self.retrieve_iambic_template(repo_name, file_path)
        if not templates:
            raise Exception("Template not found")
        template = templates[0]
        if template.template_type != template_type:
            raise Exception("Template type does not match")
        expires_at = None
        assignment = Assignment(
            user=user_email,
            expires_at=expires_at,
        )
        if duration and duration != "no_expire":
            assignment.expires_at = f"{duration}"

        template.properties.assignments.append(assignment)
        return template

    async def okta_add_user_to_group(
        self,
        template_type: str,
        repo_name: str,
        file_path: str,
        user_email: str,
        duration: int,
    ) -> None:
        # await self.clone_or_pull_git_repos()
        if template_type != "NOQ::Okta::Group":
            raise Exception("Template type is not a Okta Group")
        templates = await self.retrieve_iambic_template(repo_name, file_path)
        if not templates:
            raise Exception("Template not found")
        template = templates[0]
        if template.template_type != template_type:
            raise Exception("Template type does not match")
        expires_at = None
        group_member = UserSimple(
            username=user_email,
            expires_at=expires_at,
        )
        if duration and duration != "no_expire":
            group_member.expires_at = f"{duration}"

        template.properties.members.append(group_member)
        return template

    async def aws_iam_role_add_inline_policy(
        self,
        template_type: str,
        repo_name: str,
        file_path: str,
        user_email: dict,
        duration: str,
        all_aws_actions: list[str],
        selected_resources: list[str],
        account_name: str,
        existing_template: Optional[BaseTemplate] = None,
    ):
        # await self.clone_or_pull_git_repos()
        errors = []
        if template_type != "NOQ::AWS::IAM::Role":
            raise Exception("Template type is not an AWS IAM Role")
        templates = await self.retrieve_iambic_template(repo_name, file_path)
        if not templates:
            raise Exception("Template not found")
        if existing_template:
            template = existing_template
        else:
            template = templates[0]
        if template.template_type != template_type:
            raise Exception("Template type does not match")

        statement = PolicyStatement(
            effect="Allow",
            action=all_aws_actions,
            resource=selected_resources,
        )

        current_time = str(int(time.time()))

        policy_document = PolicyDocument(
            policy_name=f"noq_{current_time}",
            statement=[statement],
            expires_at=None,
            included_accounts=[account_name],
        )
        if duration and duration != "no_expire":
            policy_document.expires_at = f"{duration}"

        for policy in template.properties.inline_policies:
            if (
                not policy.statement == policy_document.statement
                and policy.expires_at == policy_document.expires_at
            ):
                continue
            policy_document.included_accounts.append(account_name)
            policy_document.included_accounts = list(
                set(policy_document.included_accounts)
            )

        template.properties.inline_policies.append(policy_document)
        return template

    async def google_add_user_to_group(
        self,
        template_type: str,
        repo_name: str,
        file_path: str,
        user_email: str,
        duration: int,
    ) -> None:
        # await self.clone_or_pull_git_repos()
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
            group_member.expires_at = f"{duration}"

        template.properties.members.append(group_member)
        return template

    async def create_role_access_pr(
        self, role_arns: list[str], slack_user: str, duration: int, justification: str
    ) -> None:
        errors = []
        # await self.clone_or_pull_git_repos()
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
