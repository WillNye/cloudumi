from common.config import config
from common.lib.plugins import import_class_by_name

desired_metric_plugin = config.get(
    "_global_.metrics.metrics_plugin",
    "plugins.metrics.cloudwatch.CloudWatchMetric",
)

try:
    Metric = import_class_by_name(desired_metric_plugin)
except ImportError:
    raise


def init():
    """Initialize metrics plugin."""
    return Metric
