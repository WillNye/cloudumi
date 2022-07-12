import os
from datetime import datetime


def fill_table(table, table_data, batch_size=10):
    try:
        with table.batch_writer() as writer:
            writer._flush_amount = batch_size
            for item in table_data:
                writer.put_item(Item=item)
        print(f"Loaded data into {table.name}")
    except Exception as err:
        print(f"Couldn't load data into {table.name} due to {repr(err)}")


def generate_table_data(noq_cluster: str, version: str):
    import boto3

    created_at = int((datetime.utcnow()).timestamp())
    membership_tier = 999
    created_by = "admin@noq.dev"
    ip_addr = "47.221.213.96"

    dynamodb = boto3.resource("dynamodb")
    tenant_detail_table = dynamodb.Table("tenant_details")
    static_config_table = None
    tenant_detail_docs = []

    for table in dynamodb.tables.all():
        if table.name.endswith("tenant_static_configs_v2"):
            static_config_table = table
            break

    if not static_config_table:
        print("Static config table not found")
        return

    response = static_config_table.scan(Limit=10)
    items: list[dict] = response["Items"]

    while "LastEvaluatedKey" in response:
        response = static_config_table.scan(
            Limit=10, ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    unique_tenants = set(item["tenant"]["S"] for item in items)
    for tenant in unique_tenants:
        tenant_detail_docs.append(
            {
                "name": {"S": tenant},
                "membership_tier": {"N": membership_tier},
                "is_active": {"B": True},
                "created_by": {"S": created_by},
                "created_at": {"N": created_at},
                "eula_info": {
                    "M": {
                        "signed_by": {
                            "M": {
                                "email": {"S": created_by},
                                "ip_address": {"S": ip_addr},
                            }
                        },
                        "signed_at": {"N": created_at},
                        "version": {"S": version},
                    }
                },
                "noq_cluster": {"S": noq_cluster},
            }
        )

    fill_table(tenant_detail_table, [{}])


if __name__ == "__main__":
    is_prod = False

    if is_prod:
        role = "arn:aws:iam::940552945933:role/prod_admin"
        os.environ.setdefault("AWS_PROFILE", "noq_prod")
        noq_cluster = "prod-1"
        version = ""
    else:
        role = "arn:aws:iam::759357822767:role/staging_admin"
        os.environ.setdefault("AWS_PROFILE", "noq_staging")
        noq_cluster = "staging-1"
        version = ""

    os.environ.setdefault(
        "AWS_CONTAINER_CREDENTIALS_FULL_URI", f"http://localhost:9091/ecs/{role}"
    )

    generate_table_data(noq_cluster, version)
