from typing import Dict, Optional, Union

from common.lib.singleton import Singleton


class Metric(metaclass=Singleton):
    def count(self, metric_name, tags=None):
        raise NotImplementedError

    def gauge(self, metric_name, metric_value, tags=None):
        raise NotImplementedError

    def timer(
        self,
        metric_name: str,
        tags: Optional[Union[Dict[str, Union[str, bool]], Dict[str, str]]] = None,
    ) -> None:
        raise NotImplementedError
