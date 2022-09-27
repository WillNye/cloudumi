import boto3
import click


def get_attr_name_map_nested(nested_key):
    """Future me: this is to assemble the expressionattributenames"""
    return {f"#{key}": key for key in nested_key.split(".")}


def get_attr_name_list_nested(nested_key):
    """Future me: this is to assemble the filter expression"""
    return [f"#{key}" for key in nested_key.split(".")]


@click.command()
@click.option("--key", help="The configuration key to change, can be nested")
@click.option("--value", help="The value to replace")
def main(key, value):
    client = boto3.client("dynamodb", region_name="us-west-2")
    attr_name_map = {
        "#id": "id",
    }
    attr_name_map.update(get_attr_name_map_nested(key))
    client.update_item(
        TableName="noq-dev-shared-prod-1_cloudumi_tenant_static_configs_v2",
        ExpressionAttributeNames=attr_name_map,
        ExpressionAttributeValues={
            ":value": value,
        },
        UpdateExpression=f"SET {'.'.join(get_attr_name_list_nested(key))} = :value",
        ConditionExpression="#id = master",
    )


if __name__ == "__main__":
    main()
