import datetime
import functools
import time
from functools import wraps

import boto
import boto3
import botocore.exceptions
import dateutil.tz
from botocore.config import Config
from cloudaux.aws.decorators import RATE_LIMITING_ERRORS

from common.config import config as consoleme_config
from common.lib.aws.session import get_session_for_tenant

CACHE = {}


class ConsoleMeCloudAux:
    def __init__(self, **kwargs):
        """
        cloudaux = CloudAux(
            **{'account_number': '000000000000',
               'assume_role': 'role_name',
            })
        """
        self.conn_details = {"session_name": "cloudaux", "region": "us-east-1"}
        # Let caller override session name and region
        self.conn_details.update(kwargs)

    def call(self, function_expr, **kwargs):
        """
        cloudaux = CloudAux(
            **{'account_number': '000000000000',
               'assume_role': 'role_name',
               'session_name': 'testing',
               'region': 'us-east-1',
               'tech': 'kms',
               'service_type': 'client'
            })

        cloudaux.call("list_aliases")
        cloudaux.call("kms.client.list_aliases")
        """
        if "." in function_expr:
            tech, service_type, function_name = function_expr.split(".")
        else:
            tech = self.conn_details.get("tech")
            service_type = self.conn_details.get("service_type", "client")
            function_name = function_expr

        @sts_conn(tech, service_type=service_type)
        def wrapped_method(function_name, **nargs):
            service_type = nargs.pop(nargs.pop("service_type", "client"))
            return getattr(service_type, function_name)(**nargs)

        kwargs.update(self.conn_details)
        if "tech" in kwargs:
            del kwargs["tech"]
        return wrapped_method(function_name, **kwargs)


# client = boto3_cached_conn(
#             "iam",
#             account_number=account_id,
#             assume_role=config.get_host_specific_key("policies.role_name", host),
#             region=config.region,
#             sts_client_kwargs=dict(
#                 region_name=config.region,
#                 endpoint_url=f"https://sts.{config.region}.amazonaws.com",
#             ),
#             client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
#         )


def _get_cached_creds(
    key,
    service,
    service_type,
    region,
    future_expiration_minutes,
    return_credentials,
    client_config,
    client_kwargs,
):
    role = CACHE[key]
    now = datetime.datetime.now(dateutil.tz.tzutc()) + datetime.timedelta(
        minutes=future_expiration_minutes
    )
    if role["Credentials"]["Expiration"] > now:
        if service_type == "client":
            conn = _client(service, region, role, client_config, client_kwargs)
        else:
            conn = _resource(service, region, role, client_config, client_kwargs)

        if return_credentials:
            return conn, role

        return conn

    else:
        del CACHE[key]


def _conn_kwargs(region, role, retry_config):
    kwargs = dict(region_name=region)
    kwargs.update(dict(config=retry_config))
    if role:
        kwargs.update(
            dict(
                aws_access_key_id=role["Credentials"]["AccessKeyId"],
                aws_secret_access_key=role["Credentials"]["SecretAccessKey"],
                aws_session_token=role["Credentials"]["SessionToken"],
            )
        )

    return kwargs


def _client(service, region, role, retry_config, client_kwargs, session=None):
    if not session:
        session = boto3.session.Session()
    return session.client(
        service,
        **_conn_kwargs(region, role, retry_config),
        **client_kwargs,
    )


def _resource(service, region, role, retry_config, client_kwargs, session=None):
    if not session:
        session = boto3.session.Session()
    return session.resource(
        service,
        **_conn_kwargs(region, role, retry_config),
        **client_kwargs,
    )


def boto3_cached_conn(
    service,
    host,
    service_type="client",
    future_expiration_minutes=15,
    account_number=None,
    assume_role=None,
    session_name="consoleme",
    region=consoleme_config.region,
    return_credentials=False,
    external_id=None,
    arn_partition="aws",
    read_only=False,
    retry_max_attempts=2,
    config=None,
    sts_client_kwargs=None,
    client_kwargs=None,
    session_policy=None,
    pre_assume_roles=None,
):
    """
    Used to obtain a boto3 client or resource connection.
    For cross account, provide both account_number and assume_role.

    :usage:

    # Same Account:
    client = boto3_cached_conn('iam')
    resource = boto3_cached_conn('iam', service_type='resource')

    # Cross Account Client:
    client = boto3_cached_conn('iam', account_number='000000000000', assume_role='role_name')

    # Cross Account Resource:
    resource = boto3_cached_conn('iam', service_type='resource', account_number='000000000000', assume_role='role_name')

    :param service: AWS service (i.e. 'iam', 'ec2', 'kms')
    :param service_type: 'client' or 'resource'
    :param future_expiration_minutes: Connections will expire from the cache
        when their expiration is within this many minutes of the present time. [Default 15]
    :param account_number: Required if assume_role is provided.
    :param assume_role:  Name of the role to assume into for account described by account_number.
    :param session_name: Session name to attach to requests. [Default 'cloudaux']
    :param region: Region name for connection. [Default us-east-1]
    :param return_credentials: Indicates if the STS credentials should be returned with the client [Default False]
    :param external_id: Optional external id to pass to sts:AssumeRole.
        See https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user_externalid.html
    :param arn_partition: Optional parameter to specify other aws partitions such as aws-us-gov for aws govcloud
    :param read_only: Optional parameter to specify the built in ReadOnlyAccess AWS policy
    :param retry_max_attempts: An integer representing the maximum number of retry attempts that will be made on a
        single request
    :param config: Optional botocore.client.Config
    :param sts_client_kwargs: Optional arguments to pass during STS client creation
    :return: boto3 client or resource connection
    """
    if host and pre_assume_roles is None:
        pre_assume_roles = consoleme_config.get(
            "_global_.aws.pre_role_arns_to_assume", []
        )
        pre_assume_roles.extend(
            consoleme_config.get_host_specific_key(
                "policies.pre_role_arns_to_assume", host, []
            )
        )
    elif pre_assume_roles is None:
        pre_assume_roles = []
    # TODO: This breaks when tenant employee attempts to retrieve credentials
    # if not assume_role and consoleme_config.get("_global_.environment") != "test":
    #     raise ValueError("Must provide role to assume")
    if not pre_assume_roles and consoleme_config.get("_global_.environment") != "test":
        raise Exception("Customer hasn't configured central role for Noq.")
    key = (
        host,
        account_number,
        str(pre_assume_roles),
        assume_role,
        session_name,
        external_id,
        region,
        service_type,
        service,
        arn_partition,
        read_only,
    )
    client_config = Config(retries=dict(max_attempts=retry_max_attempts))
    if not client_kwargs:
        client_kwargs = {}
    if config:
        client_config = client_config.merge(config)

    if key in CACHE:
        retval = _get_cached_creds(
            key,
            service,
            service_type,
            region,
            future_expiration_minutes,
            return_credentials,
            client_config,
            client_kwargs,
        )
        if retval:
            return retval

    sts_client_kwargs = sts_client_kwargs or {}
    sts = None
    session = get_session_for_tenant(host)
    if assume_role or pre_assume_roles:
        sts = session.client("sts", **sts_client_kwargs)
    role = None
    session_policy_needs_to_be_applied = True if session_policy else False
    if pre_assume_roles:
        for i in range(len(pre_assume_roles)):
            pre_assume_role = pre_assume_roles[i]
            assume_role_kwargs = {
                "RoleArn": pre_assume_role["role_arn"],
                "RoleSessionName": session_name,
            }

            if pre_assume_role.get("external_id"):
                assume_role_kwargs["ExternalId"] = pre_assume_role["external_id"]

            # If we're on the last pre_assume_role,  there's no other role to assume, and session policy hasn't been
            # applied, let's apply it here
            if (
                session_policy_needs_to_be_applied
                and i == len(pre_assume_roles) - 1
                and not assume_role
            ):
                assume_role_kwargs["Policy"] = session_policy
            role = sts.assume_role(**assume_role_kwargs)
            credentials = role["Credentials"]
            sts = boto3.client(
                "sts",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                **sts_client_kwargs,
            )

    if assume_role:
        # prevent malformed ARN
        if not all([account_number, assume_role]):
            raise ValueError("Account number and role to assume are both required")

        arn = "arn:{partition}:iam::{0}:role/{1}".format(
            account_number, assume_role, partition=arn_partition
        )

        assume_role_kwargs = {"RoleArn": arn, "RoleSessionName": session_name}
        if session_policy_needs_to_be_applied:
            assume_role_kwargs["Policy"] = session_policy

        if read_only:
            assume_role_kwargs["PolicyArns"] = [
                {"arn": "arn:aws:iam::aws:policy/ReadOnlyAccess"},
            ]

        if external_id:
            assume_role_kwargs["ExternalId"] = external_id

        role = sts.assume_role(**assume_role_kwargs)

    if service_type == "client":
        conn = _client(
            service, region, role, client_config, client_kwargs, session=session
        )
    elif service_type == "resource":
        conn = _resource(
            service, region, role, client_config, client_kwargs, session=session
        )
    else:
        raise Exception("Service type must be client or resource")

    if role:
        CACHE[key] = role

    if return_credentials:
        return conn, role["Credentials"]

    return conn


def rate_limited(max_attempts=None, max_delay=4):
    def decorator(f):
        metadata = {"count": 0, "delay": 0}

        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            def increase_delay(e):
                if metadata["delay"] == 0:
                    metadata["delay"] = 1
                elif metadata["delay"] < max_delay:
                    metadata["delay"] *= 2

                if max_attempts and metadata["count"] > max_attempts:
                    raise e

            metadata["count"] = 0
            while True:
                metadata["count"] += 1
                if metadata["delay"] > 0:
                    time.sleep(metadata["delay"])
                try:
                    retval = f(*args, **kwargs)
                    metadata["delay"] = 0
                    return retval
                except botocore.exceptions.ClientError as e:
                    if e.response["Error"]["Code"] not in RATE_LIMITING_ERRORS:
                        raise e
                    increase_delay(e)
                except boto.exception.BotoServerError as e:
                    if e.error_code not in RATE_LIMITING_ERRORS:
                        raise e
                    increase_delay(e)

        return decorated_function

    return decorator


def sts_conn(
    service,
    service_type="client",
    future_expiration_minutes=15,
    retry_max_attempts=10,
    config=None,
    sts_client_kwargs=None,
    client_kwargs=None,
):
    """
    This will wrap all calls with an STS AssumeRole if the required parameters are sent over.
    Namely, it requires the following in the kwargs:
    - Service Type (Required)
    - Account Number (Required for Assume Role)
    - IAM Role Name (Required for Assume Role)
    - Region (Optional, but recommended)
    - AWS Partition (Optional, defaults to 'aws' if none specified)
    - IAM Session Name (Optional, but recommended to appear in CloudTrail)
    - ReadOnly (Optional, but recommended if no write actions are being executed)

    If `force_client` is set to a boto3 client, then this will simply pass that in as the client.
    `force_client` is mostly useful for mocks and tests.
    :param service:
    :param service_type:
    :param retry_max_attempts: An integer representing the maximum number of retry attempts that will be made on a
        single request
    :param sts_client_kwargs: Optional arguments to pass during STS client creation
    :return:
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if kwargs.get("force_client"):
                kwargs[service_type] = kwargs.pop("force_client")
                kwargs.pop("account_number", None)
                kwargs.pop("region", None)
            else:
                kwargs[service_type] = boto3_cached_conn(
                    service,
                    kwargs.pop("host"),
                    service_type=service_type,
                    future_expiration_minutes=future_expiration_minutes,
                    account_number=kwargs.pop("account_number", None),
                    assume_role=kwargs.pop("assume_role", None),
                    session_name=kwargs.pop("session_name", "consoleme"),
                    external_id=kwargs.pop("external_id", None),
                    region=kwargs.pop("region", "us-east-1"),
                    arn_partition=kwargs.pop("arn_partition", "aws"),
                    read_only=kwargs.pop("read_only", False),
                    retry_max_attempts=kwargs.pop(
                        "retry_max_attempts", retry_max_attempts
                    ),
                    config=config,
                    sts_client_kwargs=kwargs.pop("sts_client_kwargs", None),
                    client_kwargs=kwargs.pop("client_kwargs", None),
                )
            return f(*args, **kwargs)

        return decorated_function

    return decorator