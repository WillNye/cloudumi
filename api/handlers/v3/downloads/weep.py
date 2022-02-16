from common.config import config
from common.handlers.base import BaseHandler
from common.lib.yaml import yaml


class WeepDownloadHandler(BaseHandler):
    async def get(self):
        host = self.ctx.host
        url = config.get_host_specific_key("url", host)
        generated_config = {
            "authentication_method": "challenge",
            "challenge_settings": {
                "user": self.user,
            },
            "consoleme_url": url,
            "server": {
                "http_timeout": 20,
                "port": 9091,
            },
        }

        install_script = (
            "mkdir -p ~/.weep ; cat <<EOF > ~/.weep/weep.yaml\n"
            f"{yaml.dump(generated_config)}"
            "EOF\n"
        )

        download_links = [
            {
                "os_name": "Mac Universal Installer",
                "download_url": (
                    "https://public-weep-binaries.s3.us-west-2.amazonaws.com/macos_installer/"
                    "weep-installer-macos-v0.3.24.pkg"
                ),
            },
            {
                "os_name": "Mac arm64",
                "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/darwin_arm64/weep",
            },
            {
                "os_name": "Mac x86_64",
                "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/darwin_x86_64/weep",
            },
            {
                "os_name": "Linux arm64",
                "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_arm64/weep",
            },
            {
                "os_name": "Linux x86_64",
                "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_x86_64/weep",
            },
            {
                "os_name": "Windows arm64",
                "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_arm64/weep.exe",
            },
            {
                "os_name": "Windows x86_64",
                "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_x86_64/weep.exe",
            },
            {
                "os_name": "Windows i386",
                "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_i386/weep.exe",
            },
        ]

        self.write(
            {
                "install_script": install_script,
                "download_links": download_links,
            }
        )
