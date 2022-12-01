from common.config import config


class ClusterConfig:
    @property
    def dynamo_retry_count(self) -> int:
        return config.get("_global_.dynamo.retry_count", 10)

    @property
    def dynamo_wait_time_between_retries(self) -> int:
        return config.get("_global_.dynamo.wait_time_between_retries", 5)
