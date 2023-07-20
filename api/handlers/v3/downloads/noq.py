import textwrap

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

        install_script_windows = textwrap.dedent(
            f"""# Create the .noq directory if it doesn't exist
$noqDirectory = "$env:USERPROFILE\\.noq"
if (!(Test-Path $noqDirectory)) {{
    New-Item -ItemType Directory -Force -Path $noqDirectory
}}

# Write the config.yaml content
$configContent = @"
{yaml.dump(generated_config)}
"@

# Write the content to the config.yaml file
Set-Content -Path "$noqDirectory\\config.yaml" -Value $configContent"""
        )

        self.write(
            {
                "install_script": install_script,
                "install_script_windows": install_script_windows,
            }
        )
