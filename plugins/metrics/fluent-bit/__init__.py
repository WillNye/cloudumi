import concurrent.futures
import datetime
import json
import os
import pathlib
import sys
from typing import Dict, Optional, Union

import sentry_sdk

from common.config import config
from plugins.metrics.base_metric import Metric

log = config.get_logger()


def log_metric_error(future):
    try:
        future.result()
    except Exception as e:
        log.error(
            {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Error sending metric",
                "error": str(e),
            },
            exc_info=True,
        )
        sentry_sdk.capture_exception()


class FluentBitMetric(Metric):
    def __init__(self):
        self.namespace = config.get("_global_.metrics.fluent-bit.namespace", "noq")
        self.executor = concurrent.futures.ThreadPoolExecutor(
            config.get("_global_.metrics.fluent-bit.max_threads", 10)
        )
        self.fluent_bit_log_file = pathlib.Path(
            config.get(
                "_global_.metrics.fluent-bit.log_file", "/var/log/saas_output.log"
            )
        )

    def send_fluent_bit_metric(self, metric_name, dimensions, unit, value):
        if not config.get("_global_.metrics.fluent-bit.enabled", True):
            return
        if not self.fluent_bit_log_file.parent.exists():
            os.makedirs(self.fluent_bit_log_file.parent, exists_ok=True)
        with open(self.fluent_bit_log_file, "a") as fpx:
            json.dump(
                {
                    datetime.datetime.utcnow().isoformat(),
                    {
                        "namespace": self.namespace,
                        "metric_name": metric_name,
                        "dimensions": dimensions,
                        "unit": unit,
                        "value": value,
                    },
                },
                fpx,
            )

    def generate_dimensions(self, tags):
        dimensions = []
        if not tags:
            return dimensions
        for name, value in tags.items():
            dimensions.append({"Name": str(name), "Value": str(value)})
        return dimensions

    def count(self, metric_name, tags=None):
        dimensions = self.generate_dimensions(tags)

        self.send_fluent_bit_metric(metric_name, dimensions, "Count", 1)

    def gauge(self, metric_name, metric_value, tags=None):
        dimensions = self.generate_dimensions(tags)

        self.send_fluent_bit_metric(metric_name, dimensions, "Count", metric_value)

    def timer(
        self,
        metric_name: str,
        tags: Optional[Union[Dict[str, Union[str, bool]], Dict[str, str]]] = None,
    ) -> None:
        dimensions = self.generate_dimensions(tags)

        self.send_fluent_bit_metric(metric_name, dimensions, "Count/Second", 1)
