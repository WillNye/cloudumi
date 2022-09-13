import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import boto3
from jinja2 import Environment, PackageLoader, select_autoescape

__package__ = "terraform_config_parser"

if len(sys.argv) >= 2:
    root_path_arg = sys.argv[1]
else:
    root_path_arg = "UNDEFINED ROOT PATH"

root_path = Path(os.getenv("CLOUDUMI_ROOT_PATH", root_path_arg))
env = Environment(loader=PackageLoader(__package__), autoescape=select_autoescape())


def simple_logger(msg: str):
    msg.replace(msg[0], msg[0].upper(), 1)
    print(f">> {msg}")


def __add_ecr_registry_aws_link(terraform_config: dict) -> dict:
    """Extract the ECR AWS link from the config output by removing the repository name from any registry URL."""
    terraform_config["registry_repository_url"] = terraform_config[
        "registry_repository_url_api"
    ].split("/")[0]
    return terraform_config


def __set_aws_profile(terraform_config: dict) -> dict:
    """Set the aws_profile from configuration hints (noq_staging or noq_prod)."""
    terraform_config["aws_profile"] = (
        "noq_staging" if terraform_config["stage"] == "staging" else "noq_prod"
    )
    return terraform_config


def __tf_tuple_strings() -> list:
    return ["tuple", ["string", "string"]]


def __tf_is_list_object(config: dict, attribute: str) -> bool:
    attr_type = config.get(attribute, {}).get("type", [])
    return type(attr_type) == list and "list" in attr_type


def parse_terraform_output():
    output_tf_json = json.loads("".join([line for line in sys.stdin]))
    parsed_output = {
        x: y.get("value")
        for x, y in output_tf_json.items()
        if y.get("type") == "string"
        or y.get("type") == "number"
        or y.get("type") == __tf_tuple_strings()
        or __tf_is_list_object(output_tf_json, x)
    }
    return parsed_output


def __get_nested_attr_from_terraform_config_list_of_dicts(
    terraform_config: dict, from_attr: str, nested_attr: str
) -> list:
    return [x.get(nested_attr) for x in terraform_config.get(from_attr, [])]


def __get_key_name_from_config(terraform_config: dict) -> str:
    namespace = terraform_config.get("namespace")
    stage = terraform_config.get("stage")
    attributes = terraform_config.get("attributes")
    if None in [namespace, stage, attributes]:
        raise RuntimeError("Missing required configuration")
    return f"{namespace}/{stage}.{attributes}.config.yaml"


def upload_configuration_to_s3(terraform_config: dict):
    my_path = Path(__file__).parent
    boto3.setup_default_session(profile_name=terraform_config["aws_profile"])
    s3 = boto3.client("s3")
    bucket_name = terraform_config["tenant_configuration_bucket_name"]
    # avoiding response
    _ = s3.put_object(
        Body=open(my_path.joinpath("configuration.yaml")).read(),
        Bucket=bucket_name,
        Key=__get_key_name_from_config(terraform_config),
    )
    simple_logger(
        f"Uploaded configuration.yaml to s3://{bucket_name}/{__get_key_name_from_config(terraform_config)}"
    )
    terraform_config["config_bucket_name"] = bucket_name
    terraform_config[
        "config_path_with_bucket"
    ] = f"s3://{bucket_name}/{__get_key_name_from_config(terraform_config)}"
    return terraform_config


def write_file(
    template_name: str,
    output_filename: str,
    terraform_config: dict,
    config_output_path: str,
):
    simple_logger(f"Writing build file to {config_output_path}/{output_filename}")
    output_path = Path(config_output_path).joinpath(output_filename)
    template = env.get_template(template_name)
    output = template.render(**terraform_config)
    with open(output_path, "w") as fp:
        fp.write(output)


def make_file_executable(config_output_path: str, output_filename: str):
    file_path = Path(config_output_path).joinpath(output_filename)
    st = os.stat(file_path)
    os.chmod(file_path, st.st_mode | stat.S_IEXEC)


def replace_str_in_attribute(
    terraform_config: dict, source: str, target: str, replace_from: str, replace_to: str
) -> dict:
    terraform_config[target] = terraform_config[source].replace(
        replace_from, replace_to
    )
    return terraform_config


def join_strings_in_attribute(
    terraform_config: dict, target: str, replace_from: list, join_char: str = ""
) -> dict:
    terraform_config[target] = join_char.join(
        [str(terraform_config.get(x, "")) for x in replace_from]
    )
    return terraform_config


def flatten_attr_from_nested_attribute(
    terraform_config: dict, from_attr: str, nested_attr: str, to_attr: str, index: int
) -> dict:
    """Extract a nested attribute from a list of dicts.

    Example:
    [
        {
            "key": "value",
        },
        {
            "key2": "value2",
        }
    ]

    Extract key/value and create a root-level entry in the terraform_config object, essentially flattening the nested struct
    Obviously pretty locked into the config output from the elasticache_nodes object, but may have other applications
    """
    elastic_cache_output = __get_nested_attr_from_terraform_config_list_of_dicts(
        terraform_config, from_attr, nested_attr
    )
    if len(elastic_cache_output) > index:
        terraform_config[to_attr] = elastic_cache_output[index]
    else:
        simple_logger(
            f"Non-existent index {index} in elastic_cache_output: {elastic_cache_output}"
        )
    return terraform_config


def is_aws_profile_present() -> bool:
    return "AWS_PROFILE" in os.environ


def get_terraform_workspace_name() -> str:
    infra_path = get_infrastructure_path()
    terraform_env_path = infra_path.joinpath(".terraform").joinpath("environment")
    if not terraform_env_path.exists():
        raise RuntimeError(
            f"No terraform environment file found under {terraform_env_path}; was terraform workspace configured?"
        )
    with open(terraform_env_path) as fp:
        terraform_workspace_name = fp.read()
    return terraform_workspace_name


def get_infrastructure_path() -> Path:
    infra_path = root_path.joinpath("deploy").joinpath("infrastructure")
    if infra_path.exists():
        return infra_path
    else:
        raise RuntimeError(
            f"The `deploy/infrastructure` folder does not exist under {str(root_path)}"
        )


def get_output_path(terraform_workspace_name: str) -> Path:
    """Checks the current Terraform workspace and derives the path to the designated live folder based on a map."""
    workspace_parts = terraform_workspace_name.split("-")
    return (
        get_infrastructure_path()
        .joinpath("live")
        .joinpath(workspace_parts[0])
        .joinpath("-".join(workspace_parts[1:]))
    )


def get_current_git_version() -> str:
    return (
        subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=root_path,
            capture_output=True,
        )
        .stdout.decode("utf-8")
        .strip()
    )


def get_current_branch_name() -> str:
    return (
        subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root_path,
            capture_output=True,
        )
        .stdout.decode()
        .replace("/", ".")
        .strip()
    )


if __name__ == "__main__":
    terraform_config = parse_terraform_output()
    config_output_path = get_output_path(get_terraform_workspace_name())
    simple_logger(f"Using config output: {config_output_path}")

    if not Path(config_output_path).is_absolute():
        simple_logger("Require an absolute output path")
        sys.exit(1)
    if not is_aws_profile_present():
        simple_logger("AWS_PROFILE is not set, cannot upload to S3; exiting")
        sys.exit(1)
    if terraform_config == {}:
        simple_logger(
            "No output from terraform, are you in the deploy/infrastructure directory?"
        )
        sys.exit(1)

    terraform_config = __add_ecr_registry_aws_link(terraform_config)
    terraform_config = __set_aws_profile(terraform_config)
    terraform_config = replace_str_in_attribute(
        terraform_config, "zone", "zone_safed", ".", "-"
    )
    terraform_config = replace_str_in_attribute(
        terraform_config, "zone", "zone_no_dot", ".", ""
    )
    terraform_config = join_strings_in_attribute(
        terraform_config,
        "central_role_name_prefix",
        ["account_id", "zone_no_dot"],
        "-",
    )
    # Instead of using the above, we'll write out the spoke_role_name_prefix too in case there are changes later
    terraform_config = join_strings_in_attribute(
        terraform_config,
        "spoke_role_name_prefix",
        ["account_id", "zone_no_dot"],
        "-",
    )
    terraform_config = join_strings_in_attribute(
        terraform_config,
        "cluster_id",
        ["zone", "namespace", "stage", "attributes"],
        "-",
    )
    terraform_config = join_strings_in_attribute(
        terraform_config,
        "cluster_id_safed",
        ["zone_safed", "namespace", "stage", "attributes"],
        "-",
    )
    terraform_config = join_strings_in_attribute(
        terraform_config,
        "cluster_id_safed_no_sep",
        ["zone_safed", "namespace", "stage", "attributes"],
    )
    terraform_config = flatten_attr_from_nested_attribute(
        terraform_config, "elasticache_nodes", "address", "elasticache_address", 0
    )
    terraform_config = flatten_attr_from_nested_attribute(
        terraform_config, "elasticache_nodes", "port", "elasticache_port", 0
    )
    write_file(
        "noq-product-configuration.yaml.jinja2",
        "configuration.yaml",
        terraform_config,
        str(Path(__file__).parent),
    )
    terraform_config = upload_configuration_to_s3(terraform_config)
    write_file(
        "noq-product-configuration.yaml.jinja2",
        "configuration.yaml",
        terraform_config,
        config_output_path,
    )
    write_file("build_file.jinja2", "BUILD", terraform_config, config_output_path)
    write_file(
        "task_definition_api.yaml.jinja2",
        "task_definition_api.yaml",
        terraform_config,
        config_output_path,
    )
    write_file(
        "task_definition_celery_flower.yaml.jinja2",
        "task_definition_celery_flower.yaml",
        terraform_config,
        config_output_path,
    )
    write_file(
        "task_definition_celery_scheduler.yaml.jinja2",
        "task_definition_celery_scheduler.yaml",
        terraform_config,
        config_output_path,
    )
    write_file(
        "task_definition_celery_worker.yaml.jinja2",
        "task_definition_celery_worker.yaml",
        terraform_config,
        config_output_path,
    )
    write_file(
        "ecs_deployer.py.jinja2",
        "ecs_deployer.py",
        terraform_config,
        config_output_path,
    )
    write_file(
        "ecs_undeployer.py.jinja2",
        "ecs_undeployer.py",
        terraform_config,
        config_output_path,
    )
    write_file(
        "test.tfvars.jinja2", "test.tfvars", terraform_config, config_output_path
    )
    write_file(
        "push_all_the_things.sh.jinja2",
        "push_all_the_things.sh",
        terraform_config,
        config_output_path,
    )
    write_file(
        "revert_all_the_things.sh.jinja2",
        "revert_all_the_things.sh",
        terraform_config,
        config_output_path,
    )
    make_file_executable(config_output_path, "push_all_the_things.sh")
    make_file_executable(config_output_path, "revert_all_the_things.sh")
    # Write configuration locally for upload to S3
