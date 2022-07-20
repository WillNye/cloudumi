from botocore.exceptions import ClientError

from common.config import config
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.tenant.models import TenantDetails

log = config.get_logger(__name__)

DOCS_BUCKET = config.get_global_s3_bucket("legal_docs")
DEFAULT_EULA_KEY = "agreements/eula.txt"


async def get_eula_key(tenant: str = None):
    if tenant:
        tenant = await TenantDetails.get(tenant)
        return tenant.eula_info.get("eula_key", DEFAULT_EULA_KEY)
    else:
        return DEFAULT_EULA_KEY


async def get_eula(version: str = None, tenant: str = None) -> str:
    eula_key = await get_eula_key(tenant)
    s3_params = {"Bucket": DOCS_BUCKET, "Key": eula_key}
    if version and version != "latest":
        s3_params["VersionId"] = version

    try:
        s3_client = boto3_cached_conn(
            "s3",
            "_global_.accounts.tenant_data",
            None,
            service_type="client",
            session_name="noq_generate_eula_link",
        )
        eula_text = await aio_wrapper(s3_client.get_object, **s3_params)
        return eula_text["Body"].read().decode("utf-8")

    except ClientError as err:
        log.error(
            {"message": "Unable to generate EULA link", "error": str(err), **s3_params}
        )


async def get_current_eula_version(tenant: str = None) -> str:
    eula_key = await get_eula_key(tenant)

    try:
        s3_client = boto3_cached_conn(
            "s3",
            "_global_.accounts.tenant_data",
            None,
            service_type="client",
            session_name="noq_get_cur_eula_version",
        )
        eula_info = await aio_wrapper(
            s3_client.get_object_attributes,
            Bucket=DOCS_BUCKET,
            Key=eula_key,
            ObjectAttributes=["ObjectSize"],
        )
        return eula_info["VersionId"]

    except ClientError as err:
        log.error({"message": "Unable to get current EULA version", "error": str(err)})
