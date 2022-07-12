from botocore.exceptions import ClientError

from common.config import config
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper

log = config.get_logger(__name__)

DOCS_BUCKET = config.get_global_s3_bucket("legal_docs")
DEFAULT_EULA_KEY = "agreements/eula.txt"


async def generate_eula_link(
    version: str = None, eula_key: str = DEFAULT_EULA_KEY
) -> str:
    s3_params = {"Bucket": DOCS_BUCKET, "Key": eula_key}
    if version:
        s3_params["VersionId"] = version

    try:
        s3_client = boto3_cached_conn(
            "s3",
            "_global_.accounts.tenant_data",
            None,
            service_type="client",
            session_name="noq_generate_eula_link",
        )
        return await aio_wrapper(
            s3_client.generate_presigned_url,
            "get_object",
            Params=s3_params,
            ExpiresIn=1800,  # 30 minutes
        )

    except ClientError as err:
        log.error(
            {"message": "Unable to generate EULA link", "error": str(err), **s3_params}
        )


async def get_current_eula_version(eula_key: str = DEFAULT_EULA_KEY) -> str:
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
