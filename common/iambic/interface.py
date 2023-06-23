import hashlib
import os
from pathlib import Path
from typing import Any, Optional

import ujson as json
from iambic.config.dynamic_config import load_config as load_config_template
from iambic.config.utils import resolve_config_template_path
from iambic.core.git import GitDiff
from iambic.core.git import retrieve_git_changes as iambic_retrieve_git_changes
from iambic.core.parser import load_templates as iambic_load_templates
from iambic.core.utils import evaluate_on_provider as iambic_evaluate_on_provider
from iambic.core.utils import gather_templates as iambic_gather_templates
from jinja2.environment import Environment
from jinja2.loaders import BaseLoader

from common.config import config
from common.config.tenant_config import TenantConfig
from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVERS
from common.iambic.git.models import IambicRepo
from common.lib.cache import store_json_results_in_redis_and_s3

log = config.get_logger(__name__)


class IambicConfigInterface:
    def __init__(self, iambic_repo: IambicRepo) -> None:
        self.iambic_repo: IambicRepo = iambic_repo
        self._iambic_config = None

    def get_full_template_path(self, template_path: str) -> str:
        if not template_path.startswith(self.iambic_repo.file_path):
            template_path = str(os.path.join(self.iambic_repo.file_path, template_path))
        return template_path

    async def get_iambic_config(self):
        if self._iambic_config:
            return self._iambic_config

        repo_path = str(self.iambic_repo.file_path)
        config_template_path = await resolve_config_template_path(repo_path)
        iambic_config = await load_config_template(
            str(config_template_path),
            configure_plugins=False,
            approved_plugins_only=True,
        )

        # This allows us to parse the templates for a provider defined in a secret
        # TODO: Better way to handle plugins that are resolved by secret
        for tp in TRUSTED_PROVIDER_RESOLVERS:
            if tp.provider == "aws":
                continue
            elif tp.provider == "azure_ad":
                provider_config = tp.iambic_plugin.provider_config(organizations=[])
            elif tp.provider == "google_workspace":
                provider_config = tp.iambic_plugin.provider_config(workspaces=[])
            elif tp.provider == "okta":
                provider_config = tp.iambic_plugin.provider_config(organizations=[])
            else:
                raise ValueError(
                    f"Unknown provider in IambicConfigInterface.get_iambic_config {tp.provider}"
                )

            iambic_config.plugin_instances.append(tp.iambic_plugin)
            iambic_config.set_config_plugin(tp.iambic_plugin, provider_config)

        self._iambic_config = iambic_config
        return self._iambic_config

    async def gather_templates(self, *args, **kwargs):
        repo_path = self.iambic_repo.file_path
        return await iambic_gather_templates(repo_path, *args, **kwargs)

    async def load_templates(
        self,
        template_paths,
        use_multiprocessing=False,
        template_map: dict = None,
        *args,
        **kwargs,
    ):
        tenant_repo_base_path_posix = Path(self.iambic_repo.file_path)
        for template_path in template_paths:
            if tenant_repo_base_path_posix not in Path(template_path).parents:
                raise Exception(
                    f"Template path {template_path} is not valid for this tenant."
                )

        if not template_map:
            iambic_config = await self.get_iambic_config()
            template_map = iambic_config.template_map
        return iambic_load_templates(
            template_paths,
            template_map,
            use_multiprocessing=use_multiprocessing,
            *args,
            **kwargs,
        )

    async def retrieve_git_changes(
        self, template_map: dict[str, Any] = None, from_sha=None, to_sha=None
    ) -> dict[str, list[GitDiff]]:
        if not template_map:
            iambic_config = await self.get_iambic_config()
            template_map = iambic_config.template_map

        return await iambic_retrieve_git_changes(
            self.iambic_repo.file_path, template_map, from_sha=from_sha, to_sha=to_sha
        )

    async def get_raw_template_yaml(self, template_path: str) -> Optional[str]:
        template_path = self.get_full_template_path(template_path)
        try:
            with open(template_path, "r") as file:
                content = file.read()
            return content
        except FileNotFoundError:
            return None

    async def retrieve_iambic_template(self, template_path: str):
        template_path = self.get_full_template_path(template_path)
        if not os.path.exists(template_path):
            raise Exception("Template not found")

        iambic_config = await self.get_iambic_config()
        return iambic_load_templates(
            [template_path], iambic_config.template_map, use_multiprocessing=False
        )

    async def cache_aws_templates(self):
        from iambic.core.utils import evaluate_on_provider

        if not self.iambic_repo.is_app_connected():
            log.error(
                {
                    "message": "No IAMbic repos configured for tenant",
                    "tenant": self.iambic_repo.repo_name,
                }
            )
            return

        tenant_name = self.iambic_repo.tenant.name
        tenant_config = TenantConfig(self.iambic_repo.tenant.name)
        tenant_templates = []
        template_dicts = []
        aws_account_dicts = []
        account_ids_to_account_names = {}
        aws_account_specific_template_types = {
            "NOQ::AWS::IAM::Role",
            "NOQ::AWS::IAM::Group",
            "NOQ::AWS::IAM::ManagedPolicy",
            "NOQ::AWS::IAM::User",
        }
        repo_name = self.iambic_repo.repo_name
        repo_path = self.iambic_repo.file_path
        # TODO: Need to have assume role access and ability to read secret
        config_template = await self.get_iambic_config()
        template_paths = await iambic_gather_templates(repo_path)
        tenant_templates.extend(
            iambic_load_templates(
                template_paths, config_template.template_map, use_multiprocessing=False
            )
        )
        aws_accounts = config_template.aws.accounts
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
            tenant=tenant_name,
        )

        await store_json_results_in_redis_and_s3(
            aws_account_dicts,
            redis_key=tenant_config.iambic_aws_accounts,
            tenant=tenant_name,
        )

        arn_typeahead = {}
        reverse_hash = {}
        reverse_hash_for_templates = {}
        for template in tenant_templates:
            arns = []
            if template.template_type in aws_account_specific_template_types:
                for aws_account in aws_accounts:
                    variables = {var.key: var.value for var in aws_account.variables}
                    variables["account_id"] = aws_account.account_id
                    variables["account_name"] = aws_account.account_name
                    if hasattr(template, "owner") and (
                        owner := getattr(template, "owner", None)
                    ):
                        variables["owner"] = owner
                    # included = await is_included_in_account(account_id, account_name, included_accounts, excluded_accounts)
                    included = evaluate_on_provider(template, aws_account)
                    if included:
                        arn = None
                        # calculate arn
                        if template.template_type == "NOQ::AWS::IAM::Role":
                            arn = f"arn:aws:iam::{aws_account.account_id}:role{template.properties.path}{template.properties.role_name}"
                        elif template.template_type == "NOQ::AWS::IAM::Group":
                            arn = f"arn:aws:iam::{aws_account.account_id}:group{template.properties.path}{template.properties.group_name}"
                        elif template.template_type == "NOQ::AWS::IAM::ManagedPolicy":
                            arn = f"arn:aws:iam::{aws_account.account_id}:policy{template.properties.path}{template.properties.policy_name}"
                        elif template.template_type == "NOQ::AWS::IAM::User":
                            arn = f"arn:aws:iam::{aws_account.account_id}:user{template.properties.path}{template.properties.user_name}"
                        else:
                            raise Exception(
                                f"Unsupported template type: {template.template_type}"
                            )
                        if arn:
                            rtemplate = Environment(loader=BaseLoader()).from_string(
                                arn
                            )
                            arn = rtemplate.render(var=variables)
                            arns.append(arn)
                pass
            d = json.loads(template.json())
            if arns:
                d["arns"] = arns
            d["repo_name"] = repo_name
            d["file_path"] = d["file_path"].replace(self.iambic_repo.file_path, "")
            d["repo_relative_file_path"] = d["file_path"].replace("/" + repo_name, "")
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
            tenant=tenant_name,
        )
        await store_json_results_in_redis_and_s3(
            reverse_hash_for_templates,
            redis_key=tenant_config.iambic_templates_reverse_hash_redis_key,
            tenant=tenant_name,
        )

        await store_json_results_in_redis_and_s3(
            arn_typeahead,
            redis_key=tenant_config.iambic_arn_typeahead_redis_key,
            tenant=tenant_name,
        )
        await store_json_results_in_redis_and_s3(
            reverse_hash,
            redis_key=tenant_config.iambic_hash_arn_redis_key,
            tenant=tenant_name,
        )

    @staticmethod
    def evaluate_on_provider(
        template: any, provider_def, exclude_import_only: bool = True
    ):
        return iambic_evaluate_on_provider(template, provider_def, exclude_import_only)
