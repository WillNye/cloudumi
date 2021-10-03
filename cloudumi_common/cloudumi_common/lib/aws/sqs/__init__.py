import ujson as json

from cloudumi_common.lib.assume_role import rate_limited, sts_conn


@sts_conn("sqs")
@rate_limited()
def get_queue_attributes(client=None, **kwargs):
    attributes = client.get_queue_attributes(**kwargs)["Attributes"]

    if attributes.get("Policy"):
        policy = json.loads(attributes["Policy"])
        attributes["Policy"] = policy

    return attributes


@sts_conn("sqs")
@rate_limited()
def get_queue_url(client=None, **kwargs):
    return client.get_queue_url(**kwargs)["QueueUrl"]


@sts_conn("sqs")
@rate_limited()
def list_queue_tags(client=None, **kwargs):
    return client.list_queue_tags(**kwargs).get("Tags", [])
