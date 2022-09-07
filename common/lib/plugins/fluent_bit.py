from common.config import config
from common.handlers.external_processes import kill_proc, launch_proc
from util.log import logger


def add_fluent_bit_service():
    enabled = config.get("_global_.metrics.fluent-bit.enabled", False)
    config_path = config.get(
        "_global_.metrics.fluent-bit.config", "/etc/fluent-bit.conf"
    )
    exe = config.get(
        "_global_.metrics.fluent-bit.exe", "/opt/fluent-bit/bin/fluent-bit"
    )
    if enabled:
        try:
            launch_proc("fluent-bit", f"{exe} -c {config_path}")
        except ValueError:
            logger.warning("Fluent-bit already running")
    else:
        logger.info("Fluent-bit not enabled")


def remove_fluent_bit_service():
    try:
        kill_proc("fluent-bit")
    except ValueError:
        logger.warning("Fluent-bit not running")
