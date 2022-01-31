from distutils.command.config import config
import json
import os
from pathlib import Path
import sys

__package__ = "terraform_config_parser"
import boto3
from jinja2 import Environment, PackageLoader, select_autoescape


configuration_bucket_name = "noq.tenant-configuration-store"
env = Environment(loader=PackageLoader(__package__), autoescape=select_autoescape())


def simple_logger(msg: str):
    msg.replace(msg[0], msg[0].upper(), 1)
    print(f">> {msg}")


def __tf_tuple_strings() -> list:
    return ["tuple", ["string", "string"]]


def parse_terraform_output():
    output_tf_json = json.loads("".join([line for line in sys.stdin]))
    parsed_output = {
        x: y.get("value")
        for x, y in output_tf_json.items()
        if y.get("type") == "string"
        or y.get("type") == "number"
        or y.get("type") == __tf_tuple_strings()
    }
    return parsed_output


def parse_elasticache_output(terraform_config: dict, attribute: str) -> list:
    return [x.get(attribute) for x, y in terraform_config.get("elasticache_nodes", [])]


def __get_key_name_from_config(terraform_config: dict) -> str:
    zone = terraform_config.get("zone")
    namespace = terraform_config.get("namespace")
    stage = terraform_config.get("stage")
    attributes = terraform_config.get("attributes")
    if None in [zone, namespace, stage, attributes]:
        raise RuntimeError("Missing required configuration")
    return f"{zone}/{namespace}/{stage}.{attributes}.config.yaml"


def upload_configuration_to_s3(terraform_config: dict):
    my_path = Path(__file__).parent
    s3 = boto3.client("s3")
    # avoiding response
    _ = s3.put_object(
        Body=open(my_path.joinpath("configuration.yaml")).read(),
        Bucket=configuration_bucket_name,
        Key=__get_key_name_from_config(terraform_config),
    )
    simple_logger(
        f"Uploaded configuration.yaml to s3://{configuration_bucket_name}/{__get_key_name_from_config(terraform_config)}"
    )
    terraform_config["config_bucket_name"] = configuration_bucket_name
    terraform_config[
        "config_path_with_bucket"
    ] = f"s3://{configuration_bucket_name}/{__get_key_name_from_config(terraform_config)}"
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


def is_aws_profile_present() -> bool:
    return "AWS_PROFILE" in os.environ


if __name__ == "__main__":
    terraform_config = parse_terraform_output()
    if not len(sys.argv) == 2:
        simple_logger(
            "Run as follows: terraform output -json | bazel run //util/terraform_config_parser <config output folder>"
        )
        sys.exit(1)
    config_output_path = sys.argv[1].rstrip("/")
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
    terraform_config = replace_str_in_attribute(
        terraform_config, "zone", "zone_safed", ".", "-"
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
    write_file("compose.yaml.jinja2", "compose.yaml", terraform_config, config_output_path)
    write_file("ecs.yaml.jinja2", "ecs.yaml", terraform_config, config_output_path)
    write_file("test.tfvars.jinja2", "test.tfvars", terraform_config, config_output_path)
    # Write configuration locally for upload to S3
