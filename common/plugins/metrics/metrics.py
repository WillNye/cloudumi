from cloudumi_common.config import config
from cloudumi_common.lib.plugins import import_class_by_name

desired_metric_plugin = config.get(
    "_global_.metrics.metrics_plugin",
    "cloudumi_plugins.plugins.metrics.default_metrics.DefaultMetric",
)

try:
    Metric = import_class_by_name(desired_metric_plugin)
except ImportError:
    raise


def init():
    """Initialize metrics plugin."""
    return Metric
