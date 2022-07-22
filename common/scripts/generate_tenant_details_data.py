import os
import sys
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


def get_existing_tenants() -> set:
    import boto3

    dynamodb = boto3.resource("dynamodb")
    static_config_table = None

    for table in dynamodb.tables.all():
        if table.name.endswith("tenant_static_configs_v2"):
            static_config_table = table
            break

    if not static_config_table:
        print("Static config table not found")
        sys.exit(1)

    response = static_config_table.scan(Limit=10)
    items: list[dict] = response["Items"]

    while "LastEvaluatedKey" in response:
        response = static_config_table.scan(
            Limit=10, ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return set(item["tenant"] for item in items)


def generate_table_data(
    boto_profile: str, tenants: set[str], noq_cluster: str, version: str
):
    import boto3

    created_at = int((datetime.utcnow()).timestamp())
    membership_tier = 999
    created_by = "admin@noq.dev"
    ip_addr = "47.221.213.96"

    boto_session = boto3.Session(profile_name=boto_profile, region_name="us-west-2")
    dynamodb = boto_session.resource("dynamodb")
    tenant_detail_table = dynamodb.Table("tenant_details")
    tenant_detail_docs = []

    for tenant in tenants:
        tenant_detail_docs.append(
            {
                "name": tenant,
                "membership_tier": membership_tier,
                "is_active": True,
                "created_by": created_by,
                "created_at": created_at,
                "eula_info": {
                    "signed_by": {"email": created_by, "ip_address": ip_addr},
                    "signed_at": created_at,
                    "version": version,
                },
                "noq_cluster": noq_cluster,
            }
        )

    fill_table(tenant_detail_table, tenant_detail_docs)


if __name__ == "__main__":
    environment = "prod"
    config_map = dict(
        prod=dict(
            primary_account="noq_prod",
            global_account="noq_global_prod",
            eula_version="sgG6_aimGlpwyUCUHywLXG6ZUtb49kB6",
            noq_cluster="prod-1",
        ),
        staging=dict(
            primary_account="noq_staging",
            global_account="noq_global_staging",
            eula_version="62j7O8SPZvZXKxGsIDniJ4acZ5jEIGix",
            noq_cluster="staging-1",
        ),
    )

    env_config = config_map[environment]
    primary_account = env_config["primary_account"]
    global_account = env_config["global_account"]
    os.environ.setdefault("AWS_PROFILE", primary_account)
    existing_tenants = get_existing_tenants()

    generate_table_data(
        global_account,
        existing_tenants,
        env_config["noq_cluster"],
        env_config["eula_version"],
    )
