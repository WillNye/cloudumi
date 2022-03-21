from typing import Any, Dict, List, Union

import boto3

from common.config import config
from common.models import (
    CognitoGroup,
    CognitoUser,
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SSOIDPProviders,
)

LOG = config.get_logger()


def __get_google_provider(
    user_pool_id: str, identity_providers: Dict[str, List[Dict[str, Any]]]
) -> GoogleOIDCSSOIDPProvider:
    client = boto3.client("cognito-idp", region_name=config.region)
    google_provider = None
    google_provider_names = [
        x.get("ProviderName")
        for x in identity_providers
        if x.get("ProviderType") == "Google"
    ]
    if google_provider_names:
        identity_provider = client.describe_identity_provider(
            UserPoolId=user_pool_id, ProviderName=google_provider_names[0]
        ).get("IdentityProvider", {})
        if identity_provider:
            google_provider = GoogleOIDCSSOIDPProvider(
                client_id=identity_provider.get("ProviderDetails", {}).get("client_id"),
                client_secret=identity_provider.get("ProviderDetails", {}).get(
                    "client_secret"
                ),
                authorize_scopes=identity_provider.get("ProviderDetails", {}).get(
                    "authorize_scopes"
                ),
                provider_name=identity_provider.get("ProviderName"),
                provider_type=identity_provider.get("ProviderType"),
            )
    return google_provider


def __get_saml_provider(
    user_pool_id: str, identity_providers: Dict[str, List[Dict[str, Any]]]
) -> SamlOIDCSSOIDPProvider:
    client = boto3.client("cognito-idp", region_name=config.region)
    saml_provider = None
    saml_provider_names = [
        x.get("ProviderName")
        for x in identity_providers
        if x.get("ProviderType") == "SAML"
    ]
    if saml_provider_names:
        identity_provider = client.describe_identity_provider(
            UserPoolId=user_pool_id, ProviderName=saml_provider_names[0]
        ).get("IdentityProvider", {})
        if identity_provider:
            saml_provider = SamlOIDCSSOIDPProvider(
                MetadataURL=identity_provider.get("ProviderDetails", {}).get(
                    "MetadataURL"
                ),
                provider_name=identity_provider.get("ProviderName"),
                provider_type=identity_provider.get("ProviderType"),
            )
    return saml_provider


def __get_oidc_provider(
    user_pool_id: str, identity_providers: Dict[str, List[Dict[str, Any]]]
) -> OIDCSSOIDPProvider:
    client = boto3.client("cognito-idp", region_name=config.region)
    oidc_provider = None
    oidc_provider_names = [
        x.get("ProviderName")
        for x in identity_providers
        if x.get("ProviderType") == "OIDC"
    ]
    if oidc_provider_names:
        identity_provider = client.describe_identity_provider(
            UserPoolId=user_pool_id, ProviderName=oidc_provider_names[0]
        ).get("IdentityProvider", {})
        if identity_provider:
            oidc_provider = OIDCSSOIDPProvider(
                client_id=identity_provider.get("ProviderDetails", {}).get("client_id"),
                client_secret=identity_provider.get("ProviderDetails", {}).get(
                    "client_secret"
                ),
                attributes_request_method=identity_provider.get(
                    "ProviderDetails", {}
                ).get("attributes_request_method"),
                oidc_issuer=identity_provider.get("ProviderDetails", {}).get(
                    "oidc_issuer"
                ),
                authorize_scopes=identity_provider.get("ProviderDetails", {}).get(
                    "authorize_scopes"
                ),
                authorize_url=identity_provider.get("ProviderDetails", {}).get(
                    "authorize_url"
                ),
                token_url=identity_provider.get("ProviderDetails", {}).get("token_url"),
                attributes_url=identity_provider.get("ProviderDetails", {}).get(
                    "attributes_url"
                ),
                jwks_uri=identity_provider.get("ProviderDetails", {}).get("jwks_uri"),
                attributes_url_add_attributes=identity_provider.get(
                    "ProviderDetails", {}
                ).get("attributes_url_add_attributes"),
                provider_name=identity_provider.get("ProviderName"),
                provider_type=identity_provider.get("ProviderType"),
            )
    return oidc_provider


def get_identity_providers(user_pool_id: str) -> SSOIDPProviders:
    """Get all identity providers.

    Queries AWS Cognito IDP for all identity providers, automatically paginates; here is the thing though,
    it only returns the first of each Google, Saml and Oidc providers. This is intentional because that
    is all we support setting at the moment. This is also why this is returning a SSOIDPProviders object
    to retain consistency within NOQ.

    :param user_pool_id: ensure this is the user pool ID not the user pool name!
    :return: SSOIDPProviders - to standardize on input output paradigms, we'll convert the raw dict to a pydantic model
    [
        {
            'ProviderName': 'auth0',
            'ProviderType': 'SAML',
            'LastModifiedDate': datetime.datetime(2022, 2, 15, 9, 56, 6, 443000, tzinfo=tzlocal()),
            'CreationDate': datetime.datetime(2022, 2, 15, 9, 56, 6, 443000, tzinfo=tzlocal())
        }
    ]
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    response = client.list_identity_providers(UserPoolId=user_pool_id)
    identity_providers = list()
    identity_providers.extend(response.get("Providers", []))
    next_token = response.get("NextToken")
    while next_token:
        response = client.list_identity_providers(
            UserPoolId=user_pool_id, NextToken=next_token
        )
        identity_providers.extend(response.get("Providers", []))
        next_token = response.get("NextToken")

    return SSOIDPProviders(
        google=__get_google_provider(user_pool_id, identity_providers),
        saml=__get_saml_provider(user_pool_id, identity_providers),
        oidc=__get_oidc_provider(user_pool_id, identity_providers),
    )


def upsert_identity_provider(user_pool_id: str, id_provider: SSOIDPProviders) -> bool:
    """Inserts or updates a identity provider.

    Some identity providers, such as SAML and possibly OIDC, can have multiple provider names, while
    Google seems to be limited to one as per experiments on the AWS UI

    Upsert is a destructive operation now, because NOQ only supports one provider at a time; however,
    Cognito supports setting multiple SAML and OIDC providers.

    So we first check if a provider is already set and delete it. We check Google as well for consistency,
    although **at this time** AWS only allows one Google provider. This is a defensive programming measure
    to avoid weird bugs later.

    :param user_pool_id: ensure this is the user pool ID not the user pool name!
    :param id_provider: the pydantic model SSOIDPProviders with one of the groups filled out (either google, saml or oidc)
    :return: True if the operation is successful - currently always returns true or raises an exception
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    identity_provider_dict = dict()
    identity_provider_type = ""
    responses = list()

    current_providers = get_identity_providers(user_pool_id)
    if id_provider.google and current_providers.google:
        delete_identity_provider(user_pool_id, current_providers.google)
    if id_provider.saml and current_providers.saml:
        delete_identity_provider(user_pool_id, current_providers.saml)
    if id_provider.oidc and current_providers.oidc:
        delete_identity_provider(user_pool_id, current_providers.oidc)

    def set_provider():
        LOG.info(
            f"Storing {identity_provider_type} Identity Provider in Cognito in user pool {user_pool_id}"
        )
        provider_name = identity_provider_dict.get("provider_name")
        provider_type = identity_provider_dict.get("provider_type")
        LOG.info(
            f"Using {provider_required} to create_identity_provider in Cognito with type {identity_provider_type}"
        )

        response = client.create_identity_provider(
            UserPoolId=user_pool_id,
            ProviderName=provider_name,
            ProviderType=provider_type,
            ProviderDetails={
                x: y
                for x, y in identity_provider_dict.items()
                if x in provider_required and y is not None
            },
        )
        return response

    if id_provider.google:
        identity_provider_dict = id_provider.google.dict()
        identity_provider_type = "Google"
        provider_required = ["client_id", "client_secret", "authorize_scopes"]
        responses.append(set_provider())
    if id_provider.saml:
        identity_provider_dict = id_provider.saml.dict()
        identity_provider_type = "SAML"
        provider_required = ["MetadataURL"]
        responses.append(set_provider())
    if id_provider.oidc:
        identity_provider_dict = id_provider.oidc.dict()
        identity_provider_type = "OIDC"
        provider_required = [
            "client_id",
            "client_secret",
            "attributes_request_method",
            "oidc_issuer",
            "authorize_scopes",
            "authorize_url",
            "token_url",
            "attributes_url",
            "jwks_uri",
            "attributes_url_add_attributes",
        ]
        responses.append(set_provider())

    LOG.info(f"Created {len(responses)} IDP: {responses}")
    return True


def delete_identity_provider(
    user_pool_id: str,
    id_provider: Union[
        GoogleOIDCSSOIDPProvider, SamlOIDCSSOIDPProvider, OIDCSSOIDPProvider
    ],
) -> bool:
    """Delete an identity provider given a specific pydantic identity model.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param id_provider: any id provider model object - see union typing hint
    :return: true if successful, currently always returns true
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    client.delete_identity_provider(
        UserPoolId=user_pool_id, ProviderName=id_provider.provider_name
    )
    return True


def get_identity_users(user_pool_id: str) -> List[CognitoUser]:
    client = boto3.client("cognito-idp", region_name=config.region)
    users = list()
    response = client.list_users(UserPoolId=user_pool_id)
    users.extend(response.get("Users", []))
    next_token = response.get("NextToken")
    while next_token:
        response = client.list_users(UserPoolId=user_pool_id, NextToken=next_token)
        users.extend(response.get("Users", []))
        next_token = response.get("NextToken")
    return [CognitoUser(**x) for x in users]


def create_identity_user(
    user_pool_id: str, user: CognitoUser, temporary_password: str
) -> CognitoUser:
    client = boto3.client("cognito-idp", region_name=config.region)
    current_users = get_identity_users(user_pool_id)
    if user.dict() in [x.dict() for x in current_users]:
        delete_identity_user(user_pool_id, user)
    delivery_mediums = list()
    if user.MFAOptions:
        delivery_mediums = [
            str(x.DeliveryMedium).split(".")[-1] for x in user.MFAOptions
        ]
    user_attributes = list()
    if user.Attributes:
        user_attributes = [dict(x) for x in user.Attributes]
    response = client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=user.Username,
        UserAttributes=user_attributes,
        TemporaryPassword=temporary_password,
        DesiredDeliveryMediums=delivery_mediums,
    )
    user_update = CognitoUser(**response.get("User", {}))
    return user_update


def delete_identity_user(user_pool_id: str, user: CognitoUser) -> bool:
    client = boto3.client("cognito-idp", region_name=config.region)
    client.admin_delete_user(UserPoolId=user_pool_id, Username=user.Username)
    return True


def get_identity_groups(user_pool_id: str) -> List[CognitoGroup]:
    client = boto3.client("cognito-idp", region_name=config.region)
    groups = list()
    response = client.list_groups(UserPoolId=user_pool_id)
    groups.extend(response.get("Groups", []))
    next_token = response.get("NextToken")
    while next_token:
        response = client.list_groups(UserPoolId=user_pool_id, NextToken=next_token)
        groups.extend(response.get("Groups", []))
        next_token = response.get("NextToken")
    return [CognitoGroup(**x) for x in groups]


def create_identity_group(user_pool_id: str, group: CognitoGroup) -> CognitoGroup:
    client = boto3.client("cognito-idp", region_name=config.region)
    current_groups = get_identity_groups(user_pool_id)
    if group.dict() in [x.dict() for x in current_groups]:
        delete_identity_group(user_pool_id, group)
    response = client.create_group(
        UserPoolId=user_pool_id,
        GroupName=group.GroupName,
        Description=group.Description,
    )
    group_update = CognitoGroup(**response.get("Group", {}))
    return group_update


def delete_identity_group(user_pool_id: str, group: CognitoGroup) -> bool:
    client = boto3.client("cognito-idp", region_name=config.region)
    client.delete_group(UserPoolId=user_pool_id, GroupName=group.GroupName)
    return True
