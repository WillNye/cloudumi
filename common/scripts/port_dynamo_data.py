import os


def fill_table(table, table_data, batch_size=10):
    try:
        with table.batch_writer() as writer:
            writer._flush_amount = batch_size
            for item in table_data:
                writer.put_item(Item=item)
        print(f"Loaded data into {table.name}")
    except Exception as err:
        print(f"Couldn't load data into {table.name} due to {repr(err)}")


def change_doc_key(old_key: str, new_key: str, dynamo_doc: dict) -> dict:
    updated_doc = dict()

    for k, v in dynamo_doc.items():
        if isinstance(v, dict):
            v = change_doc_key(old_key, new_key, v)
        elif isinstance(v, list):
            v = [
                change_doc_key(old_key, new_key, sub_v)
                if isinstance(sub_v, dict)
                else sub_v
                for sub_v in v
            ]

        new_k = new_key if k == old_key else k
        updated_doc[new_k] = v

    return updated_doc


def normalize_items(items, **kwargs) -> list[dict]:
    response = []

    for item in items:
        for old_key, new_key in kwargs.items():
            item = change_doc_key(old_key, new_key, item)
        response.append(item)

    return response


def port_dynamo_data(table_map: dict, **kwargs):
    import boto3

    dynamodb = boto3.resource("dynamodb")

    for old_table_name, new_table_name in table_map.items():
        old_table = dynamodb.Table(old_table_name)

        response = old_table.scan(Limit=10)
        old_data: list[dict] = response["Items"]

        while "LastEvaluatedKey" in response:
            response = old_table.scan(
                Limit=10, ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            old_data.extend(response.get("Items", []))

        if len(old_data) > 0:
            print(
                f"Porting {len(old_data)} items from {old_table_name} to {new_table_name}"
            )
            new_table = dynamodb.Table(new_table_name)
            fill_table(new_table, normalize_items(old_data, **kwargs))


def get_existing_tables(prefix: str = None, exclude_suffix: str = None) -> list[str]:
    import boto3

    dynamodb = boto3.resource("dynamodb")

    response = []

    for table in dynamodb.tables.all():
        if (prefix and not table.name.startswith(prefix)) or (
            exclude_suffix and table.name.endswith(exclude_suffix)
        ):
            continue
        response.append(table.name)

    return response


if __name__ == "__main__":
    is_prod = False

    if is_prod:
        role = "arn:aws:iam::940552945933:role/prod_admin"
        os.environ.setdefault("AWS_PROFILE", "prod/prod_admin")
    else:
        role = "arn:aws:iam::759357822767:role/staging_admin"
        os.environ.setdefault("AWS_PROFILE", "staging/staging_admin")

    os.environ.setdefault(
        "AWS_CONTAINER_CREDENTIALS_FULL_URI", f"http://localhost:9091/ecs/{role}"
    )

    dynamo_table_map = {
        table: f"{table}_v2" for table in get_existing_tables(exclude_suffix="v2")
    }
    port_dynamo_data(dynamo_table_map, host="tenant")
