from slack_sdk.oauth.installation_store.amazon_s3 import AmazonS3InstallationStore
from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)
from slack_sdk.oauth.installation_store.installation_store import InstallationStore
from slack_sdk.oauth.installation_store.models.installation import Installation


class NoqSlackInstallationStore(AmazonS3InstallationStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def async_save(self, installation: Installation):
        return super().save(installation)
