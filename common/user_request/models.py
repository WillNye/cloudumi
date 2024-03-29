import sys
import time

from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import ImmutableSandboxedEnvironment
from pynamodax.attributes import NumberAttribute, UnicodeAttribute
from pynamodax.indexes import AllProjection, GlobalSecondaryIndex

import common.lib.noq_json as json
from common.aws.utils import ResourceSummary
from common.config import config
from common.config.config import (
    dax_endpoints,
    dynamodb_host,
    get_dynamo_table_name,
    get_logger,
    region,
)
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.pynamo import NoqMapAttribute, NoqModel
from common.models import ExtendedRequestModel, SpokeAccount

log = get_logger("cloudumi")


class IAMRequestArnIndex(GlobalSecondaryIndex):
    # TODO: Remove this. This index won't even work because a resource can have more than 1 request
    class Meta:
        index_name = "arn-tenant-index"
        read_capacity_units = 1
        write_capacity_units = 1
        projection = AllProjection()
        region = region

    tenant = UnicodeAttribute(hash_key=True)
    arn = UnicodeAttribute(range_key=True)


class IAMRequest(NoqModel):
    class Meta:
        host = dynamodb_host
        table_name = get_dynamo_table_name("policy_requests_multitenant")
        dax_write_endpoints = dax_endpoints
        dax_read_endpoints = dax_endpoints
        fallback_to_dynamodb = True
        region = region

    tenant = UnicodeAttribute(hash_key=True)
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
    async def get(cls, tenant: str, request_id: str) -> "IAMRequest":
        """Reads a policy request from the appropriate DynamoDB table"""
        return await super(IAMRequest, cls).get(tenant, request_id)

    @classmethod
    async def write_v2(cls, extended_request: ExtendedRequestModel, tenant: str):
        """
        Writes a policy request v2 to the appropriate DynamoDB table
        """
        new_request = {
            "request_id": extended_request.id,
            "principal": json.loads(extended_request.principal.json()),
            "status": extended_request.request_status.value,
            "justification": extended_request.justification,
            "request_time": int(extended_request.timestamp.timestamp()),
            "last_updated": int(time.time()),
            "version": "2",
            "extended_request": json.loads(extended_request.json()),
            "username": extended_request.requester_email,
            "tenant": tenant,
        }

        if extended_request.principal.principal_type == "AwsResource":
            new_request["arn"] = extended_request.principal.principal_arn or "N/A"
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
            "tenant": tenant,
        }
        log.debug(log_data)

        try:
            request = cls(**new_request)
            await request.save()
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

    async def set_change_metadata(self):
        """Adds a boto3 script and an AWS CLI command for each change that can be leveraged by users.

        CLI support is currently disabled for the following commands to an issue escaping certain commands.
            resource_policy - sqs

        """
        from common.user_request.utils import get_change_arn

        disabled_cli_cmd_map = {"resource_policy": ["sqs"]}
        log_data: dict = {
            "function": f"{__name__}.{sys._getframe().f_code.co_name}",
            "request": self.extended_request.dict(),
            "tenant": self.tenant,
        }
        self_dict = self.dict()
        principal = self_dict["principal"]
        if principal.get("principal_type") in [
            "TerraformAwsResource",
            "HoneybeeAwsResourceTemplate",
        ]:
            # This method is only supported by AwsResource at this time
            return

        if not principal.get("principal_arn"):
            return

        principal_arn = principal.get("principal_arn")
        principal_summary = await ResourceSummary.set(
            self.tenant, principal_arn, region_required=True
        )

        template_env = ImmutableSandboxedEnvironment(
            loader=FileSystemLoader("common/templates"),
            extensions=["jinja2.ext.loopcontrols"],
            autoescape=select_autoescape(),
        )
        sqs_client = None
        put_policy_cli_template = None
        boto3_template = template_env.get_template("user_request_boto3.py.j2")

        for elem, change in enumerate(
            self_dict["extended_request"].get("changes", {}).get("changes", [])
        ):
            change_type = change.get("change_type")
            cli_cmd = ""
            python_script = ""
            cli_policy_document = json.dumps(
                change.get("policy", {}).get("policy_document", {}),
            )
            boto_policy_document = json.dumps(
                change.get("policy", {}).get("policy_document", {}),
                indent=2,
            )

            # Resolve the change's resource summary (parse_arn) by change type
            if get_change_arn(change) != principal_arn:
                try:
                    resource_summary = await ResourceSummary.set(
                        self.tenant, change["arn"], region_required=True
                    )
                except Exception as err:
                    # Unable to resolve the resource details for the change so set to read only
                    self_dict["extended_request"]["changes"]["changes"][elem][
                        "read_only"
                    ] = True
                    log.error(
                        {
                            "message": "Unable to get resource info for change",
                            "error": str(err),
                            **log_data,
                        }
                    )
                    continue
            else:
                resource_summary = principal_summary

            # Use the account the change will be applied to for determining if the change is read only
            account_info: SpokeAccount = (
                ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", self.tenant)
                .with_query({"account_id": resource_summary.account})
                .first
            )
            self_dict["extended_request"]["changes"]["changes"][elem][
                "read_only"
            ] = account_info.read_only

            if change_type == "generic_file":
                continue
            elif change_type in [
                "resource_policy",
                "sts_resource_policy",
                "assume_role_policy",
                "inline_policy",
            ]:
                if not put_policy_cli_template:  # Lazy load templates
                    put_policy_cli_template = template_env.get_template(
                        "user_request_aws_cli_put_policy.py.j2"
                    )

                if change_type == "sts_resource_policy":
                    resource_summary.resource_type = "iam"

                if resource_summary.resource_type == "sqs":
                    if not sqs_client:
                        try:
                            sqs_client = await aio_wrapper(
                                boto3_cached_conn,
                                resource_summary.resource_type,
                                self.tenant,
                                None,
                                account_number=resource_summary.account,
                                assume_role=ModelAdapter(SpokeAccount)
                                .load_config("spoke_accounts", self.tenant)
                                .with_query({"account_id": resource_summary.account})
                                .first.name,
                                region=resource_summary.region or config.region,
                                session_name="noq_get_request_resource_details",
                                sts_client_kwargs=dict(
                                    region_name=config.region,
                                    endpoint_url=f"https://sts.{config.region}.amazonaws.com",
                                ),
                                client_kwargs=config.get_tenant_specific_key(
                                    "boto3.client_kwargs", self.tenant, {}
                                ),
                                read_only=True,
                            )
                        except Exception as err:
                            log.error(
                                {
                                    "message": "Unable to create boto3 client",
                                    "error": str(err),
                                    **log_data,
                                }
                            )
                            continue

                    try:
                        queue_url: dict = await aio_wrapper(
                            sqs_client.get_queue_url, QueueName=resource_summary.name
                        )
                        resource_id = queue_url["QueueUrl"]
                    except Exception as err:
                        log.error(
                            {
                                "message": "Unable to retrieve SQS URL",
                                "error": str(err),
                                **log_data,
                            }
                        )
                        continue

                elif resource_summary.resource_type == "sns":
                    resource_id = resource_summary.arn

                else:
                    resource_id = resource_summary.name

                template_params = dict(
                    resource_id=resource_id,
                    resource_type=resource_summary.resource_type,
                    resouce_service=resource_summary.service,
                    policy_name=change.get("policy_name"),
                    change_type=change_type.replace("_", " "),
                )
                cli_cmd = put_policy_cli_template.render(
                    policy_document=cli_policy_document, **template_params
                )
                python_script = boto3_template.render(
                    policy_document=boto_policy_document, **template_params
                )

            elif change_type == "managed_policy_resource":  # Defer
                continue
            elif change_type == "resource_tag":  # Defer
                continue
            elif change_type == "managed_policy":  # Defer
                continue
            elif change_type == "permissions_boundary":  # Defer
                continue
            else:
                continue

            if resource_summary.resource_type not in disabled_cli_cmd_map.get(
                change_type, []
            ):
                self_dict["extended_request"]["changes"]["changes"][elem][
                    "cli_command"
                ] = cli_cmd

            self_dict["extended_request"]["changes"]["changes"][elem][
                "python_script"
            ] = python_script

        self.extended_request = self_dict["extended_request"]

    async def get_extended_request_dict(self) -> dict:
        from common.user_request.utils import ChangeValidator

        requires_update = False
        er_dict = self.extended_request.dict()

        for elem, change in enumerate(er_dict.get("changes", {}).get("changes", [])):
            if change["change_type"] == "tear_can_assume_role":
                requires_update = True
                er_dict["changes"]["changes"][elem][
                    "change_type"
                ] = "tra_can_assume_role"
            elif not ChangeValidator.is_valid(change["change_type"]):
                # TODO: Update change_type possibly to some generic typing and maybe update status
                log.warning(
                    {
                        "message": "Invalid change_type",
                        "change_type": change["change_type"],
                        "request_id": self.request_id,
                        "tenant": self.tenant,
                    }
                )

        if requires_update:
            log.debug(
                {
                    "message": "",
                    "request_id": self.request_id,
                    "tenant": self.tenant,
                }
            )
            self.extended_request = er_dict
            await self.save()

        return er_dict
