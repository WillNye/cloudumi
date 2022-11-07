from common.config import config
from common.handlers.base import BaseHandler
from common.lib.yaml import yaml


class NoqDownloadHandler(BaseHandler):
    async def get(self):
        tenant = self.ctx.tenant
        url = config.get_tenant_specific_key("url", tenant)
        generated_config = {
            "authentication_method": "challenge",
            "challenge_settings": {
                "user": self.user,
            },
            "noq_url": url,
            "server": {
                "http_timeout": 20,
                "port": 9091,
            },
        }

        install_script = (
            "mkdir -p ~/.noq ; cat <<EOF > ~/.noq/config.yaml\n"
            f"{yaml.dump(generated_config)}"
            "EOF\n"
        )

        download_links = [
            {
                "os_name": "Mac Universal Installer",
                "download_url": (
                    "https://public-noq-binaries.s3.us-west-2.amazonaws.com/macos_installer/"
                    "noq-installer-macos-v0.3.24.pkg"
                ),
            },
            {
                "os_name": "Mac arm64",
                "download_url": "https://public-noq-binaries.s3.us-west-2.amazonaws.com/darwin_arm64/noq",
            },
            {
                "os_name": "Mac x86_64",
                "download_url": "https://public-noq-binaries.s3.us-west-2.amazonaws.com/darwin_x86_64/noq",
            },
            {
                "os_name": "Linux arm64",
                "download_url": "https://public-noq-binaries.s3.us-west-2.amazonaws.com/linux_arm64/noq",
            },
            {
                "os_name": "Linux x86_64",
                "download_url": "https://public-noq-binaries.s3.us-west-2.amazonaws.com/linux_x86_64/noq",
            },
            {
                "os_name": "Windows arm64",
                "download_url": "https://public-noq-binaries.s3.us-west-2.amazonaws.com/windows_arm64/noq.exe",
            },
            {
                "os_name": "Windows x86_64",
                "download_url": "https://public-noq-binaries.s3.us-west-2.amazonaws.com/windows_x86_64/noq.exe",
            },
            {
                "os_name": "Windows i386",
                "download_url": "https://public-noq-binaries.s3.us-west-2.amazonaws.com/windows_i386/noq.exe",
            },
        ]

        self.write(
            {
                "install_script": install_script,
                "download_links": download_links,
            }
        )
