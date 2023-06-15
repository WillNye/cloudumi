from common.config import config
from common.handlers.external_processes import kill_proc, launch_proc

log = config.get_logger(__name__)


def add_fluent_bit_service():
    enabled = config.get("_global_.metrics.fluent-bit.enabled", True)
    config_path = config.get(
        "_global_.metrics.fluent-bit.config", "/etc/fluent-bit/fluent-bit.conf"
    )
    exe = config.get(
        "_global_.metrics.fluent-bit.exe", "/opt/fluent-bit/bin/fluent-bit"
    )
    if enabled:
        try:
            launch_proc("fluent-bit", f"{exe} -c {config_path}")
        except ValueError:
            log.warning("Fluent-bit already running")
    else:
        log.info("Fluent-bit not enabled")


def remove_fluent_bit_service():
    try:
        kill_proc("fluent-bit")
    except ValueError:
        log.warning("Fluent-bit not running")
