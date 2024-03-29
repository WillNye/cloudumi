from typing import Dict, Optional, Union

from common.lib.singleton import Singleton
from plugins.metrics.base_metric import Metric


class DefaultMetric(Metric, metaclass=Singleton):
    def count(self, metric_name, tags=None):
        # TODO(ccastrapel): Having Cloudwatch, Graphite, or other configurtable default metric sources here would be a
        # good idea.
        pass

    def gauge(self, metric_name, metric_value, tags=None):
        pass

    def timer(
        self,
        metric_name: str,
        tags: Optional[Union[Dict[str, Union[str, bool]], Dict[str, str]]] = None,
    ) -> None:
        pass
