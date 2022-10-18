import boto3
import click
from asgiref.sync import async_to_sync

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml


def get_attr_name_map_nested(nested_key):
    """Future me: this is to assemble the expressionattributenames"""
    return {f"#{key}": key for key in nested_key.split(".")}


def get_attr_name_list_nested(nested_key):
    """Future me: this is to assemble the filter expression"""
    return [f"#{key}" for key in nested_key.split(".")]


def get_session_name():
    client = boto3.client("sts")
    return client.get_caller_identity()["Arn"].split("/")[-1]


def set_deep(dictionary, nested_key, value):
    key_path_list = nested_key.split(".")
    pointer = dictionary
    for i, part in enumerate(key_path_list):
        if i == (len(key_path_list) - 1):
            pointer[part] = value
        else:
            if part not in pointer:
                pointer[part] = dict()
            pointer = pointer[part]


@click.command()
@click.option("--tenant", help="The tenant to receive the change")
@click.option("--key", help="The configuration key to change, can be nested")
@click.option("--value", help="The value to replace")
def main(tenant, key, value):
    session_name = get_session_name()
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    set_deep(tenant_config, key, value)
    new_config = async_to_sync(ddb.update_static_config_for_tenant)(
        yaml.dump(tenant_config), session_name, tenant
    )
    # This can become too noisy...
    print(new_config)


if __name__ == "__main__":
    main()
