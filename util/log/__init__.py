import logging

from common.config import config

logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=logging.DEBUG,
)

logging.basicConfig(level=logging.DEBUG, format=config.get("_global_.logging.format"))
logging.getLogger("_global_.urllib3.connectionpool").setLevel(logging.CRITICAL)
log = logging.getLogger()
logger = log
