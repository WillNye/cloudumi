import os
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape

from common.config import config, models
from common.lib.asyncio import aio_wrapper
from common.lib.yaml import yaml_safe as yaml
from common.models import HubAccount, SpokeAccount
from common.templates import TEMPLATE_DIR

CF_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CF_ACCOUNT_TYPES = ["central", "spoke"]
CF_CAPABILITIES = ["CAPABILITY_NAMED_IAM"]


def camel_to_snake(str_obj: str) -> str:
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", str_obj).lower()


async def load_yaml(file_name: str):
    with open(f"{CF_DATA_DIR}/{file_name}.yaml", "r") as ymlfile:
        return await aio_wrapper(yaml.load, ymlfile)


def get_stack_name(account_type: str) -> str:
    assert account_type in CF_ACCOUNT_TYPES
    return f"Noq{account_type.title()}Role"


def get_template_url(account_type: str) -> str:
    assert account_type in CF_ACCOUNT_TYPES
    return config.get(
        f"_global_.integrations.aws.registration_{account_type}_role_cf_template",
        f"https://s3.us-east-1.amazonaws.com/cloudumi-cf-templates/cloudumi_{account_type}_role.yaml",
    )


async def get_permissions() -> dict[list[str]]:
    all_permissions = await load_yaml("permissions")
    all_permissions["write"].extend(all_permissions["read"])
    all_permissions["write"] = sorted(list(set(all_permissions["write"])))
    all_permissions["read"] = sorted(list(set(all_permissions["read"])))
    return all_permissions


async def get_cf_parameters(account_type: str):
    assert account_type in CF_ACCOUNT_TYPES
    parameters = await load_yaml("parameters")
    return {**parameters["shared"], **parameters[account_type]}


async def validate_params(
    tenant: str, account_type: str, read_only_mode: bool = False
) -> dict:
    """Validates user provided values while setting params that are resolved internally like external id"""

    cf_parameters = await get_cf_parameters(account_type)
    global_vals = config.get("_global_.integrations.aws")
    # Ultimately resolve this when tenants are sharded out
    response_params = {
        "HostParameter": tenant,
        "ReadOnlyModeParameter": read_only_mode,
        "ExternalIDParameter": config.get_tenant_specific_key(
            "tenant_details.external_id", tenant
        ),
    }
    hub_account = (
        models.ModelAdapter(HubAccount).load_config("hub_account", tenant).model
    )
    if hub_account:
        response_params["CentralRoleNameParameter"] = hub_account.name

    spoke_roles = (
        models.ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant).models
    )
    if spoke_roles:
        response_params["SpokeRoleNameParameter"] = spoke_roles[0].name

    if account_type == "central":
        response_params["ClusterRoleParameter"] = global_vals.get("node_role")
    else:
        response_params["CentralRoleArnParameter"] = hub_account.role_arn

    for param_key, param_val in cf_parameters.items():
        try:
            if default_val := param_val.get("Default"):
                param_val["Type"] = type(default_val)
                response_params.setdefault(param_key, default_val)
            elif global_val := global_vals.get(
                camel_to_snake(param_key.replace("Parameter", ""))
            ):
                response_params.setdefault(param_key, global_val)

            response_param = response_params.get(param_key)
            assert response_param is not None

            if allowed_vals := param_val.get("AllowedValues"):
                assert response_param in allowed_vals

            if min_len := param_val.get("MinLength"):
                assert len(response_param) >= int(min_len)

            if max_len := param_val.get("MaxLength"):
                assert len(response_param) <= int(max_len)

            if pattern := param_val.get("AllowedPattern"):
                assert bool(re.match(pattern, response_param))

        except AssertionError as err:
            raise AssertionError(
                f'{param_key}="{param_val}": {param_val.get("ConstraintDescription", str(err))}'
            )

    return response_params


async def get_cf_tf_body(
    tenant: str, account_type: str, read_only_mode: bool = False
) -> str:
    """Returns a valid terraform cloudformation module"""

    params = await validate_params(tenant, account_type, read_only_mode)
    stack_name = get_stack_name(account_type)
    template_url = get_template_url(account_type)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        extensions=["jinja2.ext.loopcontrols"],
        autoescape=select_autoescape(),
    )
    template = await aio_wrapper(env.get_template, "cf_module.tf.j2")
    capability_str = str(
        ", ".join([f'"{capability}"' for capability in CF_CAPABILITIES])
    )
    return await aio_wrapper(
        template.render,
        stack_name=stack_name,
        template_url=template_url,
        parameters=params,
        capabilities=f"[{capability_str}]",
    )


async def get_cf_aws_cli_cmd(
    tenant: str, account_type: str, read_only_mode: bool = False
) -> str:
    """Returns the AWS CLI command to create the cloudformation stack"""
    params = await validate_params(tenant, account_type, read_only_mode)
    stack_name = get_stack_name(account_type)
    template_url = get_template_url(account_type)

    cli_cmd = "aws cloudformation create-stack \\\n"
    cli_cmd += f"--stack-name {stack_name} \\\n"
    cli_cmd += f"--template-url {template_url} \\\n"
    cli_cmd += "--parameters \\\n"
    for param_key, param_val in params.items():
        if isinstance(param_val, bool):
            param_val = str(param_val).lower()
        cli_cmd += f"  ParameterKey={param_key},ParameterValue={param_val} \\\n"
    cli_cmd += f"--capabilities {' '.join(CF_CAPABILITIES)} \\\n"
    cli_cmd += "--region us-west-2"
    return cli_cmd
