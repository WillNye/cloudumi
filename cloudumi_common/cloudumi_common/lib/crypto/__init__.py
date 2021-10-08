import os

import ed25519

from cloudumi_common.config import config
from cloudumi_common.lib.plugins import get_plugin_by_name

log = config.get_logger("consoleme")
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


class Crypto:
    def __init__(self, host) -> None:
        self.load_secrets(host)

    def load_secrets(self, host) -> None:
        if not config.get_host_specific_key(
            f"site_configs.{host}.ed25519.signing_key", host
        ):
            # Generating keys on demand. This is useful for unit tests
            self.signing_key, self.verifying_key = ed25519.create_keypair(
                entropy=os.urandom
            )
            return

        signing_key_file = os.path.expanduser(
            config.get_host_specific_key(
                f"site_configs.{host}.ed25519.signing_key", host
            )
        )
        try:
            with open(signing_key_file, "rb") as signing_file:
                signing_key_str: str = signing_file.read()
        except FileNotFoundError:
            msg = "Unable to load signing key"
            log.error(msg, exc_info=True)
            raise Exception(msg)
        self.signing_key = ed25519.SigningKey(signing_key_str)
        verifying_key_file = config.get_host_specific_key(
            f"site_configs.{host}.ed25519.verifying_key", host
        )
        try:
            verifying_key_str = open(verifying_key_file, "rb").read()
        except FileNotFoundError:
            msg = "Unable to load verifying key"
            log.error(msg, exc_info=True)
            raise Exception(msg)
        self.verifying_key = ed25519.VerifyingKey(verifying_key_str)

    def sign(self, s: str) -> bytes:
        return self.signing_key.sign(str.encode(s), encoding="base64")

    def verify(self, s, sig):
        try:
            if not s:
                return False
            self.verifying_key.verify(sig, str.encode(s), encoding="base64")
            return True
        except ed25519.BadSignatureError:
            stats.count("verify.bad_sig")
            log.error("Bad signature", exc_info=True)
            return False
