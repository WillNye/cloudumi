import copy
import datetime
import time
from typing import Tuple

from blinker import Signal

from common.config import config
from common.lib.assume_role import get_boto3_instance, rate_limited
from common.lib.aws.cached_resources.iam import (
    get_identity_arns_for_account,
    retrieve_iam_managed_policies_for_host,
)
from common.lib.cache import store_json_results_in_redis_and_s3

log = config.get_logger()


def get_epoch_authenticated(service_authenticated: int) -> Tuple[int, bool]:
    """
    Ensure service authenticated from Access Advisor is in seconds epoch

    Args:
        service_authenticated (int): The service authenticated time from Access Advisor

    Returns:
        int: The epoch time in seconds that the service was last authenticated
        bool: Whether the service authenticated was valid
    """

    BEGINNING_OF_2015_MILLI_EPOCH = 1420113600000

    dt = datetime.datetime.now(datetime.timezone.utc)
    utc_time = dt.replace(tzinfo=datetime.timezone.utc)
    current_time = int(utc_time.timestamp())
    if service_authenticated == 0:
        return 0, True

    # we have an odd timestamp, try to check
    # Sometimes AWS reports incorrect timestamps. We add current_time by a day to compensate
    elif (
        BEGINNING_OF_2015_MILLI_EPOCH
        < service_authenticated
        < (current_time * 1000) + 86400000
    ):
        return int(service_authenticated / 1000), True

    elif (
        (BEGINNING_OF_2015_MILLI_EPOCH / 1000)
        < service_authenticated
        < current_time + 86400
    ):
        return service_authenticated, True

    else:
        return -1, False


class AccessAdvisor:
    on_ready = Signal()
    on_complete = Signal()
    on_error = Signal()
    on_failure = Signal()

    def __init__(self, host):
        self.host = host
        self.max_access_advisor_job_wait = (
            5 * 60
        )  # Wait 5 minutes before giving up on jobs

    async def store_access_advisor_results(self, account_id, host, access_advisor_data):
        """
        Store Access Advisor results in S3 for identities across an account.
        """
        await store_json_results_in_redis_and_s3(
            access_advisor_data,
            s3_bucket=config.get_host_specific_key(
                "access_advisor.s3.bucket",
                host,
            ),
            s3_key=config.get_host_specific_key(
                "access_advisor.s3.file",
                host,
                "access_advisor/cache_access_advisor_{account_id}_v1.json.gz",
            ).format(account_id=account_id),
            host=host,
        )

    async def generate_and_save_access_advisor_data(self, host, account_id):
        """
        Generates and saves access advisor data for an account.
        """
        client = await get_boto3_instance(
            "iam", host, account_id, session_name="cache_access_advisor"
        )
        arns = await get_identity_arns_for_account(host, account_id)
        jobs = self._generate_job_ids(client, arns)
        access_advisor_data = self._get_job_results(client, jobs)
        if arns and not access_advisor_data:
            log.error("Didn't get any results from Access Advisor")
        await self.store_access_advisor_results(account_id, host, access_advisor_data)
        await self.generate_and_save_effective_identity_permissions(
            host, account_id, arns, access_advisor_data
        )
        return access_advisor_data

    async def generate_and_save_effective_identity_permissions(
        self, host, account_id, arns, access_advisor_data
    ):
        """
        Generates and saves the "effective permissions" for each arn in `arns`.
        """
        from common.lib.aws.unused_permissions_remover import (
            calculate_unused_policy_for_identities,
        )

        iam_policies = await retrieve_iam_managed_policies_for_host(host, account_id)
        effective_identity_permissions = await calculate_unused_policy_for_identities(
            host, arns, iam_policies, access_advisor_data
        )
        await store_json_results_in_redis_and_s3(
            effective_identity_permissions,
            s3_bucket=config.get_host_specific_key(
                "cache_iam_resources_for_account.effective_identity_permissions.s3.bucket",
                host,
            ),
            s3_key=config.get_host_specific_key(
                "cache_iam_resources_for_account.effective_identity_permissions.s3.file",
                host,
                "effective_identity_permissions/cache_effective_identity_permissions_{account_id}_v1.json.gz",
            ).format(account_id=account_id),
            host=host,
        )

    @rate_limited()
    def _generate_service_last_accessed_details(self, iam, arn):
        """Wrapping the actual AWS API calls for rate limiting protection."""
        return iam.generate_service_last_accessed_details(Arn=arn)["JobId"]

    @rate_limited()
    def _get_service_last_accessed_details(self, iam, job_id, marker=None):
        """Wrapping the actual AWS API calls for rate limiting protection."""
        params = {
            "JobId": job_id,
        }
        if marker:
            params["Marker"] = marker
        return iam.get_service_last_accessed_details(**params)

    def _generate_job_ids(self, iam, arns):
        jobs = {}
        for role_arn in arns:
            try:
                job_id = self._generate_service_last_accessed_details(iam, role_arn)
                jobs[job_id] = role_arn
            except iam.exceptions.NoSuchEntityException:
                """We're here because this ARN disappeared since the call to self._get_arns().
                Log the missing ARN and move along.
                """

                log.info(
                    "ARN {arn} found gone when fetching details".format(arn=role_arn)
                )
            except Exception as e:
                self.on_error.send(self, error=e)
                log.error(
                    "Could not gather data from {0}.".format(role_arn), exc_info=True
                )
        return jobs

    def _get_job_results(self, iam, jobs):
        access_details = {}
        job_queue = list(jobs.keys())
        last_job_completion_time = time.time()

        while job_queue:

            # Check for timeout
            now = time.time()
            if now - last_job_completion_time > self.max_access_advisor_job_wait:
                # We ran out of time, some jobs are unfinished
                self._log_unfinished_jobs(job_queue, jobs)
                break

            # Pull next job ID
            job_id = job_queue.pop()
            role_arn = jobs[job_id]
            try:
                details = self._get_service_last_accessed_details(iam, job_id)
            except Exception as e:
                self.on_error.send(self, error=e)
                log.error(
                    "Could not gather data from {0}.".format(role_arn), exc_info=True
                )
                continue

            # Check job status
            if details["JobStatus"] == "IN_PROGRESS":
                job_queue.append(job_id)
                continue

            # Check for job failure
            if details["JobStatus"] != "COMPLETED":
                log_str = "Job {job_id} finished with unexpected status {status} for ARN {arn}.".format(
                    job_id=job_id, status=details["JobStatus"], arn=role_arn
                )

                failing_arns = self.current_app.config.get("FAILING_ARNS", {})
                if role_arn in failing_arns:
                    log.info(log_str)
                else:
                    log.error(log_str)

                continue

            # Job status must be COMPLETED. Save result.
            last_job_completion_time = time.time()
            updated_list = []

            while True:
                for detail in details.get("ServicesLastAccessed"):
                    # create a copy, we're going to modify the time to epoch
                    updated_item = copy.copy(detail)

                    # AWS gives a datetime, convert to epoch
                    last_auth = detail.get("LastAuthenticated")
                    if last_auth:
                        last_auth = int(time.mktime(last_auth.timetuple()) * 1000)
                    else:
                        last_auth = 0

                    updated_item["LastAuthenticated"] = last_auth
                    updated_list.append(updated_item)
                if details.get("IsTruncated", False):
                    try:
                        details = self._get_service_last_accessed_details(
                            iam, job_id, marker=details.get("Marker")
                        )
                    except Exception:
                        log.error(
                            "Could not gather data from {0}.".format(role_arn),
                            exc_info=True,
                        )
                        break
                else:
                    break

            access_details[role_arn] = updated_list

        return access_details

    def _log_unfinished_jobs(self, job_queue, job_details):
        for job_id in job_queue:
            role_arn = job_details[job_id]
            log.error(
                "Job {job_id} for ARN {arn} didn't finish".format(
                    job_id=job_id,
                    arn=role_arn,
                )
            )
