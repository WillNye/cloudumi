from common.celery_tasks import app
from common.config import ModelAdapter, config
from common.lib.cognito import identity
from common.models import (
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SSOIDPProviders,
)

LOG = config.get_logger()


@app.task
def synchronize_cognito_sso(context: object) -> bool:
    LOG.info("Synchronizing Cognito")
    host = context.host
    user_pool_id = config.get_host_specific_key(
        "auth.cognito_config.user_pool_id", host
    )
    if not user_pool_id:
        LOG.error("Cognito user pool id not configured")
        return False
    existing_providers = identity.get_identity_providers(user_pool_id)
    configured_providers = (
        ModelAdapter(SSOIDPProviders).load_config("secrets.auth").dict
    )
    for provider in existing_providers:
        if provider.get("ProviderName") not in [
            x.get("ProviderName")
            for c in ["google", "saml", "oidc"]
            for x, _ in configured_providers.get(c, {})
        ]:
            if provider.get("ProviderType") == "Google":
                identity.delete_identity_provider(
                    user_pool_id, GoogleOIDCSSOIDPProvider(**provider)
                )
            elif provider.get("ProviderType") == "Saml":
                identity.delete_identity_provider(
                    user_pool_id, SamlOIDCSSOIDPProvider(**provider)
                )
            elif provider.get("ProviderType") == "Oidc":
                identity.delete_identity_provider(
                    user_pool_id, OIDCSSOIDPProvider(**provider)
                )
    identity.upsert_identity_provider(
        user_pool_id, ModelAdapter(SSOIDPProviders).load_config("secrets.auth").model
    )
    return True
