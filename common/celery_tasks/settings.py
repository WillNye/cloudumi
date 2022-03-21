from common.celery_tasks.celery_tasks import app
from common.config import config
from common.config.models import ModelAdapter
from common.lib.cognito import identity
from common.models import (
    CognitoGroup,
    CognitoUser,
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SSOIDPProviders,
)

LOG = config.get_logger()


@app.task
def synchronize_cognito_sso(context: dict) -> bool:
    LOG.info("Synchronizing Cognito")
    host = context.get("host")
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


@app.task
def synchronize_cognito_users(context: dict) -> bool:
    LOG.info("Synchronizing Cognito Users")
    host = context.get("host")
    user_pool_id = config.get_host_specific_key(
        "auth.cognito_config.user_pool_id", host
    )
    if not user_pool_id:
        LOG.error("Cognito user pool id not configured")
        return False
    cognito_users = identity.get_identity_users(user_pool_id)
    noq_users = (
        ModelAdapter(CognitoUser).load_config("auth.cognito_config.users", host).list
    )
    delete_users = [
        x for x in cognito_users if x.dict() not in [y.dict() for y in noq_users]
    ]
    result = False not in [identity.delete_identity_user(x) for x in delete_users]
    if result is False:
        LOG.warning("Unable to synchronize users in Cognito - pruning Cognito failed")
    add_users = [
        x for x in noq_users if x.dict() not in [y.dict() for y in cognito_users]
    ]
    result = False not in [identity.create_identity_user(x) for x in add_users]
    if result is False:
        LOG.warning(
            "Unable to synchronize users in Cognito - create operation in Cognito failed"
        )
    LOG.info(
        f"Pruned {len(delete_users)} users from Cognito and created {len(add_users)} users"
    )


@app.task
def synchronize_cognito_groups(context: dict) -> bool:
    LOG.info("Synchronizing Cognito Groups")
    host = context.get("host")
    user_pool_id = config.get_host_specific_key(
        "auth.cognito_config.user_pool_id", host
    )
    if not user_pool_id:
        LOG.error("Cognito user pool id not configured")
        return False
    cognito_groups = identity.get_identity_groups(user_pool_id)
    noq_groups = (
        ModelAdapter(CognitoGroup).load_config("auth.cognito_config.groups", host).list
    )
    delete_groups = [
        x for x in cognito_groups if x.dict() not in [y.dict() for y in noq_groups]
    ]
    result = False not in [identity.delete_identity_group(x) for x in delete_groups]
    if result is False:
        LOG.warning("Unable to synchronize groups in Cognito - pruning Cognito failed")
    add_groups = [
        x for x in noq_groups if x.dict() not in [y.dict() for y in cognito_groups]
    ]
    result = False not in [identity.create_identity_group(x) for x in add_groups]
    if result is False:
        LOG.warning(
            "Unable to synchronize groups in Cognito - create operation in Cognito failed"
        )
    LOG.info(
        f"Pruned {len(delete_groups)} groups from Cognito and created {len(add_groups)} groups"
    )
