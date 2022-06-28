# CloudUMI Scripts

## port_dynamo_data.py

> Port data from one Dynamo table to another

### Helper functions

#### `get_existing_tables(prefix: str = None, exclude_suffix: str = None) -> list[str]`

Retrieve the name of all Dynamo tables with options to filter on a prefix and exclude on a suffix.

##### Example

```python
from common.scripts.port_dynamo_data import get_existing_tables

# Get all tables that start with staging and don't end in v2
print(get_existing_tables(prefix="staging", exclude_suffix="v2"))
```

#### `port_dynamo_data(table_map: dict, **kwargs)`

Ports data from one dynamo table to the other.
The to and from tables are defined in the table map where the key is the origin table and the value is the destination table.
The kwargs are a way to recursively change key names in all dynamo docs being ported

##### Example

```python
from common.scripts.port_dynamo_data import port_dynamo_data

# Copies all documents from table_1 to new_table_1
# All the documents being copies will have any host keys replaced with tenant
example_start_doc = {
    "host": {"some": "data"},
    "other": {"stuff": {"host": {"phone": "xxxxx", "host_id": "11111"}}}
}

# It is worth pointing out host_id has remained the same because the replace is only on an exact match
# To also replace host_id you'd need to add the param host_id="tenant_id" to the port_dynamo_data call
example_end_doc = {
    "tenant": {"some": "data"},
    "other": {"stuff": {"tenant": {"phone": "xxxxx", "host_id": "11111"}}}
}

port_dynamo_data({"table_1": "new_table_1"}, host="tenant")
```
