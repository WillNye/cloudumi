import sys
from typing import Any, Dict, Optional

import boto3

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import DataNotRetrievable, MissingConfigurationValue
from common.github.models import GitHubInstall
from common.iambic_request.models import IambicRepo
from common.lib.asyncio import aio_wrapper
from common.lib.messaging import iterate_event_messages
from common.tenants.models import Tenant

log = config.get_logger(__name__)


def get_developer_queue_name() -> str:
    region = config.get("_global_.integrations.aws.region", "us-west-2")
    sts_client = boto3.client("sts", region_name=region)
    response = sts_client.get_caller_identity()
    arn = response["Arn"]
    session_name = arn.split("/")[-1]
    assert session_name.endswith("@noq.dev")
    developer_name = session_name.split("@noq.dev")[0]
    developer_name = developer_name.replace(".", "__dot__")
    return f"local-dev-{developer_name}-github-app-webhook"


def get_developer_queue_arn() -> str:
    region = config.get("_global_.integrations.aws.region", "us-west-2")
    account_id = config.get("_global_.integrations.aws.account_id")
    queue_name = get_developer_queue_name()
    developer_queue_arn = f"arn:aws:sqs:{region}:{account_id}:{queue_name}"
    return developer_queue_arn


def allow_sns_to_write_to_sqs(topic_arn, queue_arn):
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "MyPolicy",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "SQS:SendMessage",
                "Resource": queue_arn,
                "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}},
            }
        ],
    }
    return json.dumps(policy_document)


async def webhook_request_handler(request):
    """
    Note: this is where we wire up the control plane between webhook events and
    Noq SaaS Self Service request
    """

    headers = request["headers"]
    body = request["body"]

    # signature is now being validated at the lambda serverless routing layer
    # because that is deployed in a separate account. we are not re-validating
    # the payload to avoid spreading the shared secret across account.
    # payload is only propagated to the SaaS post signature validation
    # see serverless/github-app-webhook-lambda.

    github_event = json.loads(body)
    github_event_type = headers["x-github-event"]
    github_installation_id = github_event["installation"]["id"]

    # Note about why we allow a single installation id to map to multiple tenant
    # Naturally, it's not possible. In order for Noq Org GitHub app to have
    # more than one tenant: (corp) and (end-2-end-day-testing).
    tenant_github_installs = await GitHubInstall.get_with_installation_id(
        github_installation_id
    )
    if not tenant_github_installs:
        # this is an opportunity to cause denial-of-service.
        # anyone can install an app and forgot to
        # complete the installation process. For example, installer
        # does not have GitHub App install right and has not gotten
        # the install token from their GitHub Administrator yet.
        #
        # The denial of service case is adversary install our public
        # app and trigger large amount of web hook events.
        # The remediation is the lambda routing layer needs to drop
        # un-associated (adversary) github_installation requests.
        #
        # we must return to consume the event.
        log.error(
            {
                "message": "Unassociated installation_id",
                "github_installation_id": github_installation_id,
            }
        )
        return

    # push event does not carry the action key
    github_action = github_event.get("action", None)
    if github_event_type == "meta" and github_action == "deleted":
        for tenant_github_install in tenant_github_installs:
            await tenant_github_install.delete()
            return

    db_tenants = await Tenant.get_all_by_ids(
        [install.tenant_id for install in tenant_github_installs]
    )
    for db_tenant in db_tenants:
        await github_event_handler(
            github_event_type, github_action, github_event, db_tenant
        )


async def github_event_handler(
    github_event_type, github_action, github_event, db_tenant
):
    from common.celery_tasks.celery_tasks import app as celery_app

    log_data = {
        "tenant": db_tenant.name,
    }

    if github_event_type == "push":
        branch_name = github_event["ref"].split("/")[-1]
        tenant_repos = await IambicRepo.get_all_tenant_repos(db_tenant.name)
        for tenant_repo in tenant_repos:
            if tenant_repo.repo_name == github_event["repository"]["full_name"]:
                if tenant_repo.default_branch_name == branch_name:
                    celery_app.send_task(
                        "common.celery_tasks.celery_tasks.run_all_iambic_tasks_for_tenant",
                        kwargs={"tenant": db_tenant.name},
                    )
                break

        return

    if github_event_type == "pull_request" and github_action == "synchronize":
        # FIXME hm, what's to do if someone push a change to the request branch
        # is calling sync_iambic_templates_for_tenant sufficient.
        login = github_event["sender"]["login"]
        repo_name = (github_event["repository"]["full_name"],)
        pr_number = (github_event["pull_request"]["number"],)
        log.info(
            {
                **log_data,
                "message": f"out-of-band changes have triggered by {login}",
                "repo_name": repo_name,
                "pr_number": pr_number,
            }
        )
    elif (github_event_type == "pull_request" and github_action == "closed") or (
        github_event_type == "pull_request_review"
        and github_action == "submitted"
        and github_event["review"]["state"] == "approved"
    ):
        if github_event_type == "pull_request":
            # pull request type GitHub event does not provide any approved by information.
            approved_by = None
        else:
            # per review, there is only 1 approver; however, there can be multiple review, and
            # saas may need to aggregate them for audit? maybe. especially for complex review
            # rule that requires multiple approvers.
            approved_by = github_event["review"]["user"]["login"]

        if isinstance(approved_by, str):
            approved_by = [approved_by]

        celery_app.send_task(
            "common.celery_tasks.celery_tasks.update_self_service_state",
            kwargs={
                "tenant_id": db_tenant.id,
                "repo_name": github_event["repository"]["full_name"],
                "pull_request": github_event["pull_request"]["number"],
                "pr_created_at": github_event["pull_request"]["created_at"],
                "approved_by": approved_by,
                "is_merged": bool(github_event["pull_request"]["merged_at"]),
                "is_closed": bool(github_event["pull_request"]["closed_at"]),
            },
        )
    elif (
        github_event_type == "installation_repositories" and github_action == "removed"
    ):
        # TODO any clean up method if we need to call if webhook event
        # notify us repos is removed
        # repositories_removed = github_event["repositories_removed"]
        pass


async def handle_github_webhook_event_queue(
    celery_app,
    max_num_messages_to_process: Optional[int] = None,
) -> Dict[str, Any]:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }
    assert log_data

    if not max_num_messages_to_process:
        max_num_messages_to_process = config.get(
            "_global_.integrations.github.webhook_event_buffer.max_num_messages_to_process",
            100,
        )

    queue_arn = config.get(
        "_global_.integrations.github.webhook_event_buffer.queue_arn",
        None,
    )

    if config.is_development:
        queue_arn = get_developer_queue_arn()

    if not queue_arn and not config.is_development:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`_global_.integrations.github.webhook_event_buffer.queue_arn`"
        )
    queue_region = queue_arn.split(":")[3]

    sqs_client = boto3.client("sqs", region_name=queue_region)

    queue_url = config.get(
        "_global_.integrations.github.webhook_event_buffer.queue_url", None
    )
    if not queue_url and not config.is_development:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`_global_.integrations.github.webhook_event_buffer.queue_url`"
        )
    if config.is_development:
        queue_name = queue_arn.split(":")[-1]
        queue_url_res = await aio_wrapper(
            sqs_client.get_queue_url, QueueName=queue_name
        )
        queue_url = queue_url_res.get("QueueUrl")
        if not queue_url:
            raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")

    messages_awaitable = await aio_wrapper(
        sqs_client.receive_message,
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=0,  # we are using short pooling because this task is scheduled in high priority queue and frequently.
    )
    messages = messages_awaitable.get("Messages", [])
    num_events = 0
    while messages:
        if num_events >= max_num_messages_to_process:
            break
        processed_messages = []

        for message in iterate_event_messages(queue_arn, messages):
            num_events += 1
            try:
                # BEGIN Actual work done, the
                webhook_request = message["body"]
                await webhook_request_handler(webhook_request)
                # END special sauce, the rest is boilerplate

            except Exception as e:
                # We setup the dead letter queue re-drive policy in terraform.
                # How it works is typically after 4 (or N) attempt to consume
                # it will automatically move to the associated DLQ
                log.error({**log_data, "error": e}, exc_info=True)
            finally:
                message_id = message.get("message_id")
                receipt_handle = message.get("receipt_handle")
                processed_messages.append(
                    {
                        "Id": message_id,
                        "ReceiptHandle": receipt_handle,
                    }
                )
        if processed_messages:
            await aio_wrapper(
                sqs_client.delete_message_batch,
                QueueUrl=queue_url,
                Entries=processed_messages,
            )
        messages_awaitable = await aio_wrapper(
            sqs_client.receive_message,
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=0,  # we are using short pooling because this task is scheduled in high priority queue and frequently.
        )
        messages = messages_awaitable.get("Messages", [])
    return {"message": "Successfully processed all messages", "num_events": num_events}
