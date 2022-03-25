from common.celery_tasks.celery_tasks import app
from common.config import config
from common.config.models import ModelAdapter
from common.lib.cognito import identity
from common.models import CognitoGroup, CognitoUser, SSOIDPProviders

LOG = config.get_logger()


@app.task
def synchronize_cognito_sso(context: dict) -> bool:
    LOG.info("Synchronizing Cognito")
    host = context.get("host")
    static_config = config.get_tenant_static_config_from_dynamo(host)
    user_pool_id = (
        static_config.get("auth", {}).get("cognito_config", {}).get("user_pool_id")
    )
    if not user_pool_id:
        LOG.error("Cognito user pool id not configured")
        return False
    existing_providers = identity.get_identity_providers(user_pool_id)
    configured_providers = (
        ModelAdapter(SSOIDPProviders).load_config("secrets.auth", host).model
    )
    client_id = config.get_host_specific_key("aws.cognito_config.client_id", host)
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


@app.task
def synchronize_cognito_users(context: dict) -> bool:
    LOG.info("Synchronizing Cognito Users")
    host = context.get("host")
    static_config = config.get_tenant_static_config_from_dynamo(host)
    user_pool_id = (
        static_config.get("auth", {}).get("cognito_config", {}).get("user_pool_id")
    )
    if not user_pool_id:
        LOG.error("Cognito user pool id not configured")
        return False
    cognito_users = identity.get_identity_users(user_pool_id)
    noq_users = (
        ModelAdapter(CognitoUser).load_config("aws.cognito.accounts.users", host).models
    )
    delete_users = [x for x in cognito_users if x not in [y for y in noq_users]]
    result = False not in [
        identity.delete_identity_user(user_pool_id, x) for x in delete_users
    ]
    if result is False:
        LOG.warning("Unable to synchronize users in Cognito - pruning Cognito failed")
    add_users = [x for x in noq_users if x not in [y for y in cognito_users]]
    result = False not in [
        identity.create_identity_user(user_pool_id, x) for x in add_users
    ]
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
    static_config = config.get_tenant_static_config_from_dynamo(host)
    user_pool_id = (
        static_config.get("auth", {}).get("cognito_config", {}).get("user_pool_id")
    )
    if not user_pool_id:
        LOG.error("Cognito user pool id not configured")
        return False
    cognito_groups = identity.get_identity_groups(user_pool_id)
    noq_groups = (
        ModelAdapter(CognitoGroup)
        .load_config("aws.cognito.accounts.groups", host)
        .models
    )
    delete_groups = [x for x in cognito_groups if x not in [y for y in noq_groups]]
    result = False not in [
        identity.delete_identity_group(user_pool_id, x) for x in delete_groups
    ]
    if result is False:
        LOG.warning("Unable to synchronize groups in Cognito - pruning Cognito failed")
    add_groups = [x for x in noq_groups if x not in [y for y in cognito_groups]]
    result = False not in [
        identity.create_identity_group(user_pool_id, x) for x in add_groups
    ]
    if result is False:
        LOG.warning(
            "Unable to synchronize groups in Cognito - create operation in Cognito failed"
        )
    LOG.info(
        f"Pruned {len(delete_groups)} groups from Cognito and created {len(add_groups)} groups"
    )
