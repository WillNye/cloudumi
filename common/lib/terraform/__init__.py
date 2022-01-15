import os
import sys
import tempfile
from typing import Optional, Union

# Hacky way to add a policy
from checkov.common.graph.db_connectors.networkx.networkx_db_connector import (
    NetworkxConnector,
)
from checkov.terraform.graph_builder.local_graph import TerraformLocalGraph
from checkov.terraform.graph_manager import TerraformGraphManager

from common.config import config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.git import clone_repo
from common.lib.terraform.models import (
    TerraformResourceModel,
    TerraformResourceModelArray,
)

log = config.get_logger()


async def cache_terraform_resources(host):
    terraform_resources = TerraformResourceModelArray(terraform_resources=[])

    for repository in config.get_host_specific_key(
        "cache_resource_templates.repositories", host, []
    ):
        if repository.get("type") == "git":
            result = await cache_terraform_resources_for_repository(repository, host)
            terraform_resources.terraform_resources.extend(result.terraform_resources)

    await store_json_results_in_redis_and_s3(
        terraform_resources.dict(),
        redis_key=config.get_host_specific_key(
            "cache_terraform_resources.redis.key",
            host,
            f"{host}_cache_terraform_resources_v1",
        ),
        s3_bucket=config.get_host_specific_key(
            "cache_terraform_resources.s3.bucket", host
        ),
        s3_key=config.get_host_specific_key(
            "cache_terraform_resources.s3.file",
            host,
            "cache_terraform_resources/cache_terraform_resources_v1.json.gz",
        ),
        host=host,
    )
    return terraform_resources


async def retrieve_cached_terraform_resources(
    host,
    resource_type: Optional[str] = None,
    resource: Optional[str] = None,
    repository_name: Optional[str] = None,
    return_first_result=False,
) -> Optional[Union[TerraformResourceModelArray, TerraformResourceModel]]:
    matching_resources = []
    terraform_resources_d = await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get_host_specific_key(
            "cache_terraform_resources.redis.key",
            host,
            f"{host}_cache_terraform_resources_v1",
        ),
        s3_bucket=config.get_host_specific_key(
            "cache_terraform_resources.s3.bucket", host
        ),
        s3_key=config.get_host_specific_key(
            "cache_terraform_resources.s3.file",
            host,
            "cache_terraform_resources/cache_terraform_resources_v1.json.gz",
        ),
        host=host,
    )

    terraform_resources = TerraformResourceModelArray.parse_obj(terraform_resources_d)
    for tf_resource in terraform_resources.terraform_resources:
        if resource_type and not tf_resource.resource_type == resource_type:
            continue
        if resource and not tf_resource.resource == resource:
            continue
        if repository_name and not tf_resource.repository_name == repository_name:
            continue
        if return_first_result:
            return tf_resource
        matching_resources.append(tf_resource)
    if return_first_result:
        return None
    return TerraformResourceModelArray(terraform_resources=matching_resources)


async def cache_terraform_resources_for_repository(
    repository, host
) -> TerraformResourceModelArray:
    """
    Example configuration:
    cache_resource_templates:
      repositories:
        - name: consoleme
          type: git
          repo_url: https://github.com/Netflix/consoleme
          web_path: https://github.com/Netflix/consoleme
          resource_formats:
            - terraform
          authentication_settings:
            email: "terraform@noq.dev"
          resource_type_parser:
            terraform:
              path_suffix: .tf
    """

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "repository": repository,
        "host": host,
    }
    if repository["type"] not in ["git"]:
        raise Exception("Unsupported repository type")
    resource_formats = repository["resource_formats"]
    if "terraform" not in resource_formats:
        log.debug(
            {
                **log_data,
                "message": "Terraform resources are not configured for this repository",
            }
        )
        return TerraformResourceModelArray(terraform_resources=[])
    tempdir = tempfile.mkdtemp()
    repo_url = repository["repo_url"]
    repo = clone_repo(repo_url, tempdir)
    repo.config_writer().set_value("user", "name", "Noq").release()
    email = repository["authentication_settings"].get("email")
    if email:
        repo.config_writer().set_value("user", "email", email).release()

    db_connector = NetworkxConnector()
    graph_manager = TerraformGraphManager(source="Terraform", db_connector=db_connector)
    graph_class = TerraformLocalGraph
    parsing_errors = {}
    _, tf_definitions = graph_manager.build_graph_from_source_directory(
        source_dir=repo.working_dir,
        local_graph_class=graph_class,
        download_external_modules=False,
        external_modules_download_path=".external_modules",
        parsing_errors=parsing_errors,
        excluded_paths=[],
        vars_files=None,
    )
    all_tf_resources = []
    for file, tf_definition in tf_definitions.items():
        filepath = file.replace(repo.working_dir + os.sep, "")
        if not tf_definition.get("resource"):
            continue
        for resources_details in tf_definition["resource"]:
            # Only support AWS IAM Role currently
            for resource_type, resources in resources_details.items():
                if resource_type != "aws_iam_role":
                    continue
                for resource_name, resource_details in resources.items():
                    resource_identifier = resource_name

                    all_tf_resources.append(
                        TerraformResourceModel.parse_obj(
                            {
                                "resource": resource_identifier,
                                "display_text": resource_identifier,
                                "resource_url": repository["repo_url"],
                                "repository_name": repository["name"],
                                "repository_url": repository["repo_url"],
                                "repository_path": filepath,
                                "resource_type": "AWS::IAM::Role",
                            }
                        )
                    )

    log.debug({**log_data, "message": "Finished caching Terraform resources"})

    return TerraformResourceModelArray(terraform_resources=all_tf_resources)
