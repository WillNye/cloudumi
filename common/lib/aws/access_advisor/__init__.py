import copy
import time

from blinker import Signal

from common.config import config
from common.lib.assume_role import rate_limited

log = config.get_logger()


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

    def generate_access_advisor_data(self, iam, arns):
        jobs = self._generate_job_ids(iam, arns)
        details = self._get_job_results(iam, jobs)
        if arns and not details:
            log.error("Didn't get any results from Access Advisor")
        return details

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
                if details.get("Truncated", False):
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
