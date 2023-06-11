import datetime
import hashlib
import os
import time
from pathlib import Path
from typing import Optional

import httpx
import jwt
import pytz
import ujson as json
from git import Repo
from git.exc import GitCommandError
from github import Github
from iambic.config.dynamic_config import load_config as load_config_template
from iambic.config.utils import resolve_config_template_path
from iambic.core.git import retrieve_git_changes as iambic_retrieve_git_changes
from iambic.core.models import BaseTemplate
from iambic.core.parser import load_templates as iambic_load_templates

# TODO: Still need to get Iambic installed in the SaaS. This is a localhost hack.
from iambic.core.utils import evaluate_on_provider as iambic_evaluate_on_provider
from iambic.core.utils import gather_templates as iambic_gather_templates
from iambic.plugins.v0_1_0.aws.iam.policy.models import (
    ManagedPolicyDocument,
    PolicyDocument,
    PolicyStatement,
)
from iambic.plugins.v0_1_0.aws.identity_center.permission_set.models import (
    PermissionSetAccess,
)
from iambic.plugins.v0_1_0.aws.models import Tag
from iambic.plugins.v0_1_0.google_workspace.group.models import GroupMember
from iambic.plugins.v0_1_0.okta.group.models import UserSimple
from iambic.plugins.v0_1_0.okta.models import Assignment
from jinja2.environment import Environment
from jinja2.loaders import BaseLoader

from common.aws.accounts.models import AWSAccount
from common.config import models
from common.config.globals import (
    GITHUB_APP_ID,
    GITHUB_APP_PRIVATE_KEY,
    TENANT_STORAGE_BASE_PATH,
)
from common.config.tenant_config import TenantConfig
from common.github.models import GitHubInstall
from common.lib.cache import store_json_results_in_redis_and_s3
from common.lib.yaml import yaml
from common.models import IambicRepoDetails
from common.tenants.models import Tenant

IAMBIC_REPOS_BASE_KEY = "iambic_repos"


async def get_github_repos(access_token):
    # maximum supported value is 100
    # github default is 30
    # to test, change this to 1 to test pagination stitching response
    # why 100? with gzip compression, it's better to have
    # more results in single response, and let's compression take advantage
    # of repeated strings.
    per_page = 100
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
        "Accept-Encoding": "gzip, deflate, br",
        "per_page": f"{per_page}",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/installation/repositories", headers=headers
        )
        response.raise_for_status()
        content_so_far = response.json()
        # handle pagination: https://docs.github.com/en/rest/guides/using-pagination-in-the-rest-api?apiVersion=2022-11-28
        while "next" in response.links:
            response = await client.get(response.links["next"]["url"], headers=headers)
            response.raise_for_status()
            content_so_far["repositories"].extend(response.json()["repositories"])
    return content_so_far


class IambicGit:
    def __init__(self, tenant: str) -> None:
        self.tenant: str = tenant
        self.git_repositories = []
        self.tenant_repo_base_path: str = os.path.expanduser(
            os.path.join(TENANT_STORAGE_BASE_PATH, tenant, "iambic_template_repos")
        )
        os.makedirs(os.path.dirname(self.tenant_repo_base_path), exist_ok=True)
        self.repos = {}
        self.db_tenant = None
        self.installation_id = None

    async def is_github_app_connected(self):
        """Use this function to handle the case github_app connectivity is missing

        Note: This only checks against cloudumi database knowledge and does not
        reach out to Github. Github side will have transient failure. The database
        check is more repeatable.
        """
        # do not mutate the self object in this function
        db_tenant = await Tenant.get_by_name(self.tenant)
        gh_installation = await GitHubInstall.get(db_tenant)
        return bool(gh_installation)

    async def get_access_token(self):
        if not self.db_tenant:
            self.db_tenant = await Tenant.get_by_name(self.tenant)
        if not self.installation_id:
            self.gh_installation = await GitHubInstall.get(self.db_tenant)
            if not self.gh_installation:
                raise Exception(
                    f"Github App not connected for tenant {self.tenant}. "
                    "Please connect the Github App before using this feature."
                )
            self.installation_id = self.gh_installation.installation_id

        # Generate the JWT
        now = int(time.time())
        payload = {
            "iat": now,  # Issued at time
            "exp": now + (10 * 60),  # JWT expiration time (10 minute maximum)
            "iss": GITHUB_APP_ID,  # GitHub App's identifier
        }
        jwt_token = jwt.encode(payload, GITHUB_APP_PRIVATE_KEY, algorithm="RS256")

        # Use the JWT to authenticate as the GitHub App
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.machine-man-preview+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
                headers=headers,
            )
        response.raise_for_status()
        access_token = response.json()["token"]

        return access_token

    async def get_repos(self):
        access_token = await self.get_access_token()
        return await get_github_repos(access_token)

    def get_iambic_repo_path(self, repo_name):
        return os.path.join(self.tenant_repo_base_path, repo_name)

    async def load_iambic_config(self, repo_name: str):
        repo_path = self.get_iambic_repo_path(repo_name)
        config_template_path = await resolve_config_template_path(str(repo_path))
        return await load_config_template(
            config_template_path,
            configure_plugins=False,
            approved_plugins_only=True,
        )

    async def gather_templates(self, repo_name: str, *args, **kwargs):
        repo_path = self.get_iambic_repo_path(repo_name)
        return await iambic_gather_templates(repo_path, *args, **kwargs)

    def load_templates(
        self, template_paths, use_multiprocessing=False, *args, **kwargs
    ):
        tenant_repo_base_path_posix = Path(self.tenant_repo_base_path)
        for template_path in template_paths:
            if tenant_repo_base_path_posix not in Path(template_path).parents:
                raise Exception(
                    f"Template path {template_path} is not valid for this tenant."
                )
        return iambic_load_templates(
            template_paths, use_multiprocessing=use_multiprocessing, *args, **kwargs
        )

    async def set_git_repositories(self) -> None:
        self.git_repositories: list[IambicRepoDetails] = (
            models.ModelAdapter(IambicRepoDetails)
            .load_config(IAMBIC_REPOS_BASE_KEY, self.tenant)
            .models
        )

    async def retrieve_git_changes(
        self, repo_name: str, from_sha=None, to_sha=None
    ) -> None:
        repo_path = self.get_iambic_repo_path(repo_name)
        return await iambic_retrieve_git_changes(
            repo_path, from_sha=from_sha, to_sha=to_sha
        )

    def evaluate_on_provider(
        self, template: str, provider_def, exclude_import_only: bool = True
    ):
        return iambic_evaluate_on_provider(template, provider_def, exclude_import_only)

    async def get_default_branch(self, repo) -> str:
        return next(
            ref for ref in repo.remotes.origin.refs if ref.name == "origin/HEAD"
        ).ref.name

    async def get_raw_template_yaml(
        self, repo_name: str, file_path: str
    ) -> Optional[str]:
        await self.set_git_repositories()
        for repository in self.git_repositories:
            if repository.repo_name != repo_name:
                continue
            repo_path = os.path.join(self.tenant_repo_base_path, repo_name, file_path)
            try:
                with open(repo_path, "r") as file:
                    content = file.read()
                return content
            except FileNotFoundError:
                return None

    async def get_last_updated(self, repo_name: str, file_path: str) -> Optional[str]:
        await self.set_git_repositories()
        for repository in self.git_repositories:
            if repository.repo_name != repo_name:
                continue
            repo_path = os.path.join(self.tenant_repo_base_path, repo_name)
            repo = Repo(repo_path)
            commits = repo.iter_commits(paths=file_path)
            for commit in commits:
                committed_date = commit.committed_datetime
                return committed_date.astimezone(pytz.UTC).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )

    async def generate_github_link(
        self, org_name: str, repo_name: str, default_branch: str, file_path: str
    ) -> str:
        return f"https://github.com/{org_name}/{repo_name}/blob/{default_branch}/{file_path}"

    async def clone_or_pull_git_repos(self) -> None:
        return  # TODO: Remove this. For testing purposes only.
        # To set role access, modify a template manually in tenant local storage
        # and CloudUmi will honor it because of this bypass. Needs official fix in
        # https://noqdev.atlassian.net/browse/EN-2148

        # TODO: Formalize the model for secrets
        await self.set_git_repositories()
        for repository in self.git_repositories:
            repo_name = repository.repo_name
            access_token = await self.get_access_token()
            repo_path = self.get_iambic_repo_path(repository.repo_name)
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
                    "gh": Github(access_token),
                    "default_branch": default_branch,
                }
            except GitCommandError as e:
                if "already exists and is not an empty directory" not in e.stderr:
                    raise
                # TODO: async
                repo = Repo(repo_path)
                for remote in repo.remotes:
                    if "origin" in remote.name:
                        with remote.config_writer as cw:
                            cw.set("url", git_uri)
                        remote.fetch()
                default_branch = await self.get_default_branch(repo)
                default_branch_name = default_branch.split("/")[-1]
                repo.git.checkout(default_branch_name)
                repo.git.reset("--hard", default_branch)
                repo.git.pull()

                self.repos[repo_name] = {
                    "repo": repo,
                    "path": repo_path,
                    "gh": Github(access_token),
                    "default_branch": default_branch,
                }
        return

    async def gather_templates_for_tenant(self):
        tenant_config = TenantConfig(self.tenant)
        await self.set_git_repositories()
        for repository in self.git_repositories:
            repo_name = repository.repo_name
            repo_path = self.get_iambic_repo_path(repository.repo_name)
            # TODO: Need to have assume role access and ability to read secret
            # for Iambic config and templates to load
            config_template = await self.load_iambic_config(repository.repo_name)
            template_paths = await iambic_gather_templates(repo_path)
            self.templates = iambic_load_templates(
                template_paths, use_multiprocessing=False
            )
            template_dicts = []

            aws_account_specific_template_types = {
                "NOQ::AWS::IAM::Role",
                "NOQ::AWS::IAM::Group",
                "NOQ::AWS::IAM::ManagedPolicy",
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
                account_ids_to_account_names,
                redis_key=tenant_config.iambic_aws_account_ids_to_names,
                tenant=self.tenant,
            )

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
                                arn = rtemplate.render(var=variables)
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
            await self.load_iambic_config(repository.repo_name)
            return iambic_load_templates([full_path], use_multiprocessing=False)
        raise Exception("Template not found")

    async def sync_aws_accounts(self):
        await self.set_git_repositories()
        if not self.db_tenant:
            self.db_tenant = await Tenant.get_by_name(self.tenant)
        for repository in self.git_repositories:
            config_template = await self.load_iambic_config(repository.repo_name)
            aws_accounts = config_template.aws.accounts
            known_accounts = await AWSAccount.get_by_tenant(self.db_tenant)
            remove_accounts = [
                x
                for x in known_accounts
                if x.name not in [x.account_name for x in aws_accounts]
            ]
            if remove_accounts:
                await AWSAccount.delete(
                    self.db_tenant, [x.account_id for x in remove_accounts]
                )
            if aws_accounts:
                await AWSAccount.bulk_create(
                    self.db_tenant,
                    [
                        {"name": x.account_name, "account_id": x.account_id}
                        for x in aws_accounts
                    ],
                )

    async def sync_identity_roles(self):
        from common.lib.iambic.sync import sync_identity_roles, sync_role_access

        await self.set_git_repositories()
        if not self.db_tenant:
            self.db_tenant = await Tenant.get_by_name(self.tenant)
        for repository in self.git_repositories:
            config_template = await self.load_iambic_config(repository.repo_name)
            await sync_identity_roles(self.db_tenant, config_template)
            await sync_role_access(self.db_tenant, config_template)

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

    async def aws_add_user_to_permission_set(
        self,
        template_type: str,
        repo_name: str,
        file_path: str,
        user_email: dict,
        duration: str,
        selected_aws_accounts,
        existing_template: Optional[BaseTemplate] = None,
    ):
        if template_type != "NOQ::AWS::IdentityCenter::PermissionSet":
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
        included_accounts = []
        for account in selected_aws_accounts:
            included_accounts.append(account["value"])
        new_access_rule = PermissionSetAccess(
            users=[user_email],
            included_accounts=included_accounts,
        )

        if duration and duration != "no_expire":
            new_access_rule.expires_at = f"{duration}"

        template.access_rules.append(new_access_rule)
        return template

    async def aws_iam_role_add_update_remove_tag(
        self,
        template_type: str,
        repo_name: str,
        file_path: str,
        user_email: dict,
        tag_action: str,
        tag_key: str,
        tag_value: str,
        included_accounts: list[str],
        excluded_accounts: list[str] = [],
        duration: str = None,
        existing_template: Optional[BaseTemplate] = None,
    ):
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
        # TODO: Handle tag expiry
        # if duration and duration != "no_expire":
        #     policy_document.expires_at = f"{duration}"
        updated = False
        to_remove = []
        if template.properties.tags:
            for tag in template.properties.tags:
                if tag.key != tag_key:
                    continue
                if sorted(included_accounts) != sorted(tag.included_accounts):
                    continue
                if sorted(excluded_accounts) != sorted(tag.excluded_accounts):
                    continue

                if tag_action == "create_update":
                    tag.value = tag_value
                    updated = True
                elif tag_action == "remove":
                    to_remove.append(tag)
        for tag in to_remove:
            template.properties.tags.remove(tag)
            updated = True
        if tag_action == "create_update" and not updated:
            new_tag = Tag(
                key=tag_key,
                value=tag_value,
                included_accounts=included_accounts,
                excluded_accounts=excluded_accounts,
            )
            if not template.properties.tags:
                template.properties.tags = []
            template.properties.tags.append(new_tag)
        return template

    async def aws_iam_managed_policy_add_policy_statement(
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
        if template_type != "NOQ::AWS::IAM::ManagedPolicy":
            raise Exception("Template type is not an AWS IAM Managed Policy")
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

        if duration and duration != "no_expire":
            statement.expires_at = f"{duration}"

        existing_policy_document = template.properties.policy_document
        if not existing_policy_document:
            existing_policy_document = ManagedPolicyDocument()
        # if isinstance(existing_policy_document, ManagedPolicyDocument):
        #     existing_policy_document = [existing_policy_document]
        appended_to_existing_policy = False
        for existing_statement in template.properties.policy_document.statement:
            if not (
                existing_statement == statement
                and existing_statement.expires_at == statement.expires_at
            ):
                continue
            statement.included_accounts.append(account_name)
            statement.included_accounts = sorted(list(set(statement.included_accounts)))
            appended_to_existing_policy = True
        if not appended_to_existing_policy:
            statement.included_accounts = [account_name]
        template.properties.policy_document.statement.append(statement)
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

        appended_to_existing_policy = False
        for policy in template.properties.inline_policies:
            if not (
                policy.statement == policy_document.statement
                and policy.expires_at == policy_document.expires_at
            ):
                continue
            policy.included_accounts.append(account_name)
            policy.included_accounts = sorted(list(set(policy.included_accounts)))
            appended_to_existing_policy = True
        if not appended_to_existing_policy:
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
        # TODO: Hardcoded
        gh_repo = gh.get_repo("noqdev/noq-templates")
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
