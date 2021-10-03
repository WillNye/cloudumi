from cloudumi_common.lib.assume_role import rate_limited, sts_conn


@sts_conn("s3")
@rate_limited()
def list_buckets(client=None, **kwargs):
    return client.list_buckets()


@sts_conn("s3")
@rate_limited()
def get_bucket_location(client=None, **kwargs):
    """
    Bucket='string'
    """
    return client.get_bucket_location(**kwargs)


@sts_conn("s3")
@rate_limited()
def get_bucket_policy(client=None, **kwargs):
    """
    Bucket='string'
    """
    return client.get_bucket_policy(**kwargs)


@sts_conn("s3", service_type="resource")
@rate_limited()
def get_bucket_resource(bucket_name, resource=None, **kwargs):
    return resource.Bucket(bucket_name)


@sts_conn("s3")
@rate_limited()
def get_bucket_tagging(client=None, **kwargs):
    """
    Bucket='string'
    """
    return client.get_bucket_tagging(**kwargs)
