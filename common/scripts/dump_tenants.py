import json
from io import StringIO
from uuid import UUID

import boto3
from ruamel.yaml import YAML


class CloudUmiYaml(YAML):
    def dump(self, data, stream=None, **kw):
        inefficient = False
        if stream is None:
            inefficient = True
            stream = StringIO()
        YAML.dump(self, data, stream, **kw)
        if inefficient:
            return stream.getvalue()


typ = "rt"
yaml = CloudUmiYaml(typ=typ)
yaml_safe = CloudUmiYaml(typ="safe")
yaml_safe.register_class(UUID)
yaml_pure = CloudUmiYaml(typ="safe", pure=True)
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.representer.ignore_aliases = lambda *data: True

# Ability to serialize UUID objects
yaml.register_class(UUID)

yaml.width = 4096


# @tenacity.retry(tenacity.wait_exponential(multiplier=3, min=4, max=120))
def get_tenants_configs(
    client,
    static_configs_table_name="noq-dev-shared-prod-1_cloudumi_tenant_static_configs_v2",
):
    paginator = client.get_paginator("scan")
    responses = []
    for resp in paginator.paginate(
        TableName=static_configs_table_name,
        ExpressionAttributeNames={
            "#id": "id",
        },
        ExpressionAttributeValues={
            ":id": {"S": "master"},
        },
        FilterExpression="#id = :id",
    ):
        responses.extend(resp.get("Items", []))
    return responses


def main():
    client = boto3.client("dynamodb", region_name="us-west-2")
    configs = get_tenants_configs(client)
    tenants = []
    for config in configs:
        cfg_deserialized = yaml.load(config.get("config", {}).get("S", ""))
        tenants.append(cfg_deserialized.get("url"))
    return tenants


if __name__ == "__main__":
    tenants = main()
    print(json.dumps(tenants))
