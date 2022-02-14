from common.config import config
from common.handlers.base import BaseHandler


class WeepDownloadHandler(BaseHandler):
    def get(self):
        host = self.ctx.host
        url = config.get_host_specific_key("url", host)
        generated_config = f"""authentication_method: challenge
challenge_settings:
  user: {self.user}
consoleme_url: {url}
server:
  http_timeout: 20
  port: 9091
"""

        os_configurations = {
            [
                {
                    "os_name": "Mac Universal Installer",
                    "download_url": (
                        "https://public-weep-binaries.s3.us-west-2.amazonaws.com/macos_installer/"
                        "weep-installer-macos-v0.3.24.pkg"
                    ),
                }
            ],
            [
                {
                    "os_name": "Mac arm64",
                    "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/darwin_arm64/weep",
                }
            ],
            [
                {
                    "os_name": "Mac x86_64",
                    "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/darwin_x86_64/weep",
                }
            ],
            [
                {
                    "os_name": "Linux arm64",
                    "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_arm64/weep",
                }
            ],
            [
                {
                    "os_name": "Linux x86_64",
                    "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/linux_x86_64/weep",
                }
            ],
            [
                {
                    "os_name": "Windows arm64",
                    "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_arm64/weep.exe",
                }
            ],
            [
                {
                    "os_name": "Windows x86_64",
                    "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_x86_64/weep.exe",
                }
            ],
            [
                {
                    "os_name": "Windows i386",
                    "download_url": "https://public-weep-binaries.s3.us-west-2.amazonaws.com/windows_i386/weep.exe",
                }
            ],
        }

        self.write(
            {
                "generated_config": generated_config,
                "os_configurations": os_configurations,
            }
        )
