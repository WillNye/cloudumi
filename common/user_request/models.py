import json
import sys
import time

from pynamodax.attributes import NumberAttribute, UnicodeAttribute
from pynamodax.indexes import AllProjection, GlobalSecondaryIndex

from common.config.config import (
    dax_endpoints,
    dynamodb_host,
    get_dynamo_table_name,
    get_logger,
)
from common.lib.asyncio import aio_wrapper
from common.lib.pynamo import NoqMapAttribute, NoqModel
from common.models import ExtendedRequestModel

log = get_logger("cloudumi")


class IAMRequestArnIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = "arn-host-index"
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()

    host = UnicodeAttribute(hash_key=True)
    arn = UnicodeAttribute(range_key=True)


class IAMRequest(NoqModel):
    class Meta:
        host = dynamodb_host
        table_name = get_dynamo_table_name("policy_requests_multitenant")
        dax_write_endpoints = dax_endpoints
        dax_read_endpoints = dax_endpoints
        fallback_to_dynamodb = True

    host = UnicodeAttribute(hash_key=True)
    request_id = UnicodeAttribute(range_key=True)
    arn = UnicodeAttribute()
    extended_request = NoqMapAttribute()
    principal = NoqMapAttribute()
    justification = UnicodeAttribute()
    status = UnicodeAttribute()
    username = UnicodeAttribute()
    version = UnicodeAttribute()
    request_time = NumberAttribute()
    last_updated = NumberAttribute()

    arn_index = IAMRequestArnIndex()

    @classmethod
    async def get(cls, host: str, arn=None, request_id=None):
        """Reads a policy request from the appropriate DynamoDB table"""
        if not arn and not request_id:
            raise Exception("Must pass in ARN or Policy Request ID")
        elif arn and request_id:
            raise Exception("Only ARN OR Policy Request ID can be provided")

        if request_id:
            return super(IAMRequest, cls).get(host, request_id)

        results = await aio_wrapper(cls.arn_index.query, host, cls.arn == arn)
        results = [r for r in results]
        if len(results) == 1:
            return results[0]

    @classmethod
    async def write_v2(cls, extended_request: ExtendedRequestModel, host: str):
        """
        Writes a policy request v2 to the appropriate DynamoDB table
        """
        new_request = {
            "request_id": extended_request.id,
            "principal": extended_request.principal.dict(),
            "status": extended_request.request_status.value,
            "justification": extended_request.justification,
            "request_time": int(extended_request.timestamp.timestamp()),
            "last_updated": int(time.time()),
            "version": "2",
            "extended_request": json.loads(extended_request.json()),
            "username": extended_request.requester_email,
            "host": host,
        }

        if extended_request.principal.principal_type == "AwsResource":
            new_request["arn"] = extended_request.principal.principal_arn
        elif extended_request.principal.principal_type == "HoneybeeAwsResourceTemplate":
            repository_name = extended_request.principal.repository_name
            resource_identifier = extended_request.principal.resource_identifier
            new_request["arn"] = f"{repository_name}-{resource_identifier}"
        else:
            raise Exception("Invalid principal type")

        log_data = {
            "function": f"{__name__}.{cls.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Writing policy request v2 to Dynamo",
            "request": new_request,
            "host": host,
        }
        log.debug(log_data)

        try:
            request = cls(**new_request)
            await aio_wrapper(request.save)
            log_data[
                "message"
            ] = "Successfully finished writing policy request v2 to Dynamo"
            log.debug(log_data)
            return request
        except Exception as e:
            log_data["message"] = "Error occurred writing policy request v2 to Dynamo"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            error = f"{log_data['message']}: {str(e)}"
            raise Exception(error)
