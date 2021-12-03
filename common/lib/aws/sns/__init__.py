from common.lib.assume_role import rate_limited, sts_conn
from common.lib.aws.aws_paginate import aws_paginated


@sts_conn("sns")
@aws_paginated(
    "Topics",
    request_pagination_marker="NextToken",
    response_pagination_marker="NextToken",
)
@rate_limited()
def list_topics(client=None, **kwargs):
    return client.list_topics(**kwargs)


@sts_conn("sns")
@rate_limited()
def get_topic_attributes(client=None, **kwargs):
    return client.get_topic_attributes(**kwargs)["Attributes"]
