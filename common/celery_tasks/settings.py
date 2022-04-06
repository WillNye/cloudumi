from common.celery_tasks.celery_tasks import app
from common.config import config
from common.config.models import ModelAdapter
from common.lib.cognito import identity
from common.models import SSOIDPProviders

LOG = config.get_logger()


@app.task
def synchronize_cognito_sso(context: dict) -> bool:
    LOG.info("Synchronizing Cognito")
    host = context.get("host")
    static_config = config.get_tenant_static_config_from_dynamo(host)
    user_pool_id = (
        static_config.get("secrets", {})
        .get("cognito", {})
        .get("config", {})
        .get("user_pool_id")
    )
    if not user_pool_id:
        LOG.error("Cognito user pool id not configured")
        return False
    existing_providers = identity.get_identity_providers(user_pool_id)
    configured_providers = (
        ModelAdapter(SSOIDPProviders).load_config("secrets.auth", host).model
    )
    client_id = config.get_host_specific_key(
        "secrets.cognito.config.user_pool_client_id", host
    )
    if existing_providers.google and not configured_providers.google:
        identity.disconnect_idp_from_app_client(
            user_pool_id, client_id, existing_providers.google
        )
        identity.delete_identity_provider(user_pool_id, existing_providers.google)
    elif existing_providers.saml and not configured_providers.saml:
        identity.disconnect_idp_from_app_client(
            user_pool_id, client_id, existing_providers.saml
        )
        identity.delete_identity_provider(user_pool_id, existing_providers.saml)
    elif existing_providers.oidc and not configured_providers.oidc:
        identity.disconnect_idp_from_app_client(
            user_pool_id, client_id, existing_providers.oidc
        )
        identity.delete_identity_provider(user_pool_id, existing_providers.oidc)
    identity.upsert_identity_provider(user_pool_id, configured_providers)
    if configured_providers.google and not existing_providers.google:
        identity.connect_idp_to_app_client(
            user_pool_id, client_id, configured_providers.google
        )
    if configured_providers.saml and not existing_providers.saml:
        identity.connect_idp_to_app_client(
            user_pool_id, client_id, configured_providers.saml
        )
    if configured_providers.oidc and not existing_providers.oidc:
        identity.connect_idp_to_app_client(
            user_pool_id, client_id, configured_providers.oidc
        )
    return True
