from distutils.command.config import config
import json
from pathlib import Path
import sys
__package__ = "terraform_config_parser"
from jinja2 import Environment, PackageLoader, select_autoescape


env = Environment(
    loader=PackageLoader(__package__),
    autoescape=select_autoescape()
)


def simple_logger(msg: str):
    msg.replace(msg[0], msg[0].upper(), 1)
    print(f">> {msg}")


def parse_terraform_output():
    return json.loads("".join([line for line in sys.stdin]))


def write_file(template_name: str, output_filename: str, terraform_config: dict, config_output_path: str):
    simple_logger(f"Writing build file to {config_output_path}/{output_filename}")
    output_path = Path(config_output_path).joinpath(output_filename)
    template = env.get_template(template_name)
    output = template.render(**terraform_config)
    with open(output_path, "w") as fp:
        fp.write(output)


if __name__ == "__main__":
    terraform_config = parse_terraform_output()
    if not len(sys.argv) == 2:
        simple_logger("Run as follows: terraform output -json | bazel run //util/terraform_config_parser <config output folder>")
        sys.exit(1)
    config_output_path = sys.argv[1]
    write_file("build_file.jinja2", "BUILD", terraform_config, config_output_path)
    write_file("compose.yaml.jinja2", "compose.yaml", terraform_config, config_output_path)
    write_file("ecs.yaml.jinja2", "ecs.yaml", terraform_config, config_output_path)
