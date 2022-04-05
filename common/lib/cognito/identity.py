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
) -> Union[GoogleOIDCSSOIDPProvider, None]:
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
) -> Union[SamlOIDCSSOIDPProvider, None]:
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
) -> Union[OIDCSSOIDPProvider, None]:
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


def get_user_pool_client_id(user_pool_id: str, client_name: str) -> str:
    """Get the user pool client ID for a given client name.

    :param user_pool_id: the user pool ID
    :param client_name: the client name
    :return: the user pool ID
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    response = client.list_user_pool_clients(UserPoolId=user_pool_id)
    for client in response.get("UserPoolClients", []):
        if client.get("ClientName") == client_name:
            return client.get("ClientId")
    next_token = response.get("NextToken")
    while next_token:
        response = client.list_user_pool_clients(
            UserPoolId=user_pool_id, NextToken=next_token
        )
        for client in response.get("UserPoolClients", []):
            if client.get("ClientName") == client_name:
                return client.get("ClientId")
        next_token = response.get("NextToken")
    raise Exception(f"Could not find user pool ID for client {client_name}")


def get_user_pool_client(user_pool_id: str, client_id: str) -> dict:
    """Get a specific client from a user pool.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param client_id: the client ID to get
    :return: the client object
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    response = client.describe_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id
    )
    return response


def connect_idp_to_app_client(
    user_pool_id: str,
    client_id: str,
    idp: Union[GoogleOIDCSSOIDPProvider, SamlOIDCSSOIDPProvider, OIDCSSOIDPProvider],
) -> bool:
    """Connects the IDP to the app client.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param client_id: the client ID of the app client
    :return: true if successful, currently always returns true
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    user_pool_supported_idp = (
        get_user_pool_client(user_pool_id, client_id)
        .get("UserPoolClient", {})
        .get("SupportedIdentityProviders")
    )
    if not user_pool_supported_idp:
        user_pool_supported_idp = list()
    if idp.provider_name not in user_pool_supported_idp:
        user_pool_supported_idp.append(idp.provider_name)
        client.update_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            SupportedIdentityProviders=user_pool_supported_idp,
        )
    return True


def disconnect_idp_from_app_client(
    user_pool_id: str,
    client_id: str,
    idp: Union[GoogleOIDCSSOIDPProvider, SamlOIDCSSOIDPProvider, OIDCSSOIDPProvider],
) -> bool:
    """Disconnect an IDP from the app client.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param client_id: the client ID of the app client
    :param idp: one of the NOQ internal identity provider objects
    :return: reflects that the desired state is reached, meaning that the idp is not connected to the app client
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    user_pool_supported_idp = (
        get_user_pool_client(user_pool_id, client_id)
        .get("UserPoolClient", {})
        .get("SupportedIdentityProviders")
    )
    if not user_pool_supported_idp:
        return True
    if idp.provider_name in user_pool_supported_idp:
        user_pool_supported_idp.remove(idp.provider_name)
        client.update_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            SupportedIdentityProviders=user_pool_supported_idp,
        )
    return True


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
        disconnect_idp_from_app_client(
            user_pool_id,
        )
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


def get_identity_user_groups(
    user_pool_id: str, user: CognitoUser
) -> List[CognitoGroup]:
    """Get the group assignments for a user pool.

    :param user_pool_id: the user pool ID
    :param user: the user for which to extract group assignments
    :return: a list of dictionaries representing the group assignments
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    groups = list()
    response = client.admin_list_groups_for_user(
        Username=user.Username, UserPoolId=user_pool_id
    )
    groups.extend([CognitoGroup(**x) for x in response.get("Groups", [])])
    next_token = response.get("NextToken")
    while next_token:
        response = client.admin_list_groups_for_user(
            Username=user.Username, UserPoolId=user_pool_id
        )
        groups.extend([CognitoGroup(**x) for x in response.get("Groups", [])])
        next_token = response.get("NextToken")
    return groups


def get_identity_users(user_pool_id: str) -> List[CognitoUser]:
    """Get Cognito users and format as pydantic CognitoUser objects.

    Retrieves all cognito users and returns them in a list as CognitoUser
    objects.

    :param user_pool_id: the current user pool id
    :return: a list of CognitoUser objects
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    LOG.info(f"{__name__} using boto3 client in region {config.region}")
    users = list()
    response = client.list_users(UserPoolId=user_pool_id)
    users.extend(response.get("Users", []))
    next_token = response.get("NextToken")
    while next_token:
        response = client.list_users(UserPoolId=user_pool_id, NextToken=next_token)
        users.extend(response.get("Users", []))
        next_token = response.get("NextToken")
    cognito_users = [CognitoUser(**x) for x in users]
    for cognito_user in cognito_users:
        cognito_user.Groups = [
            x.GroupName for x in get_identity_user_groups(user_pool_id, cognito_user)
        ]
    return cognito_users


def create_identity_user(user_pool_id: str, user: CognitoUser) -> CognitoUser:
    """Create a Cognito user account.

    Note: this account will delete an already existing user and recreate it. This
    uses the admin_create_user functionality, side-stepping the user sign up process.

    :param user_pool_id: the id of the user pool that should have the new user
    :param user: a CognitoUser object that is validated and describes the new user
    :return: an updated CognitoUser object that may contain additional info from AWS
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    LOG.info(f"{__name__} using boto3 client in region {config.region}")
    current_users = get_identity_users(user_pool_id)
    if user in [x for x in current_users]:
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
        TemporaryPassword=user.TemporaryPassword,
        DesiredDeliveryMediums=delivery_mediums,
    )
    user_update = CognitoUser(**response.get("User", {}))
    if user.Groups:
        LOG.info(f"Adding groups {user.Groups} to user {user.Username}")
        create_identity_user_groups(
            user_pool_id, user_update, [CognitoGroup(GroupName=x) for x in user.Groups]
        )
    return user_update


def delete_identity_user(user_pool_id: str, user: CognitoUser) -> bool:
    """Delete a Cognito user.

    Uses the admin_delete_user functionality to delete a user from the
    Cognito database.

    :param user_pool_id: the id of the user pool from which to delete the user
    :param user: a CognitoUser object that describes the user
    :return: true if successful
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    LOG.info(f"{__name__} using boto3 client in region {config.region}")
    client.admin_delete_user(UserPoolId=user_pool_id, Username=user.Username)
    return True


def create_identity_user_groups(
    user_pool_id: str, user: CognitoUser, groups: List[CognitoGroup]
) -> bool:
    """Assign a user to a group.

    :param user_pool_id: the id of the user pool from which to delete the user
    :param user: a CognitoUser object that describes the user
    :param groups: a list of CognitoGroup objects that describe the groups to which the user should be added
    :return: true if successful
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    LOG.info(f"{__name__} using boto3 client in region {config.region}")
    for group in groups:
        try:
            client.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=user.Username,
                GroupName=group.GroupName,
            )
        except client.exceptions.UserNotFoundException:
            LOG.warning(f"User {group.Username} not found in user pool {user_pool_id}.")
            return False
        except client.exceptions.ResourceNotFoundException:
            LOG.warning(
                f"Group {group.GroupName} not found in user pool {user_pool_id}."
            )
            return False
        except client.exceptions.ResourceConflictException:
            LOG.warning(f"User {group.Username} already in group {group.GroupName}.")
            return False
        except Exception:
            LOG.exception(
                f"Error assigning user {group.Username} to group {group.GroupName}"
            )
            return False
    return True


def upsert_identity_user_group(user_pool_id: str, user: CognitoUser) -> bool:
    """Removes old identity groups and creates ones that don't exist for the provided cognito user

    :param user_pool_id: the id of the user pool from which to delete the user
    :param user: a CognitoUser object that describes the user
    :param request_groups: a list of CognitoGroup objects that describe the groups to which the user should be added
    :return: true if successful
    """
    existing_groups = get_identity_user_groups(user_pool_id, user)

    for group in existing_groups:
        if group not in user.Groups:
            delete_identity_group(user_pool_id, group)

    return create_identity_user_groups(
        user_pool_id,
        user,
        [group for group in user.Groups if group not in existing_groups],
    )


def get_identity_groups(user_pool_id: str) -> List[CognitoGroup]:
    """Get Cognito groups.

    :param user_pool_id: the id of the user pool from which to get groups
    :return: a list of CognitoGroup objects
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    LOG.info(f"{__name__} using boto3 client in region {config.region}")
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
    """Create a Cognito group.

    :param user_pool_id: the id of the user pool in which to create the group
    :param group: a CognitoGroup object that describes the group
    :return: an updated group object that may contain additional information from AWS
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    LOG.info(f"{__name__} using boto3 client in region {config.region}")
    current_groups = get_identity_groups(user_pool_id)
    if group in [x for x in current_groups]:
        delete_identity_group(user_pool_id, group)
    response = client.create_group(
        UserPoolId=user_pool_id,
        GroupName=group.GroupName,
        Description=group.Description,
    )
    group_update = CognitoGroup(**response.get("Group", {}))
    return group_update


def delete_identity_group(user_pool_id: str, group: CognitoGroup) -> bool:
    """Delete a Cognito group

    :param user_pool_id: the id of the user pool that contains the group to be deleted
    :param group: a CognitoGroup object that describes the group
    :return: true if successful
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    LOG.info(f"{__name__} using boto3 client in region {config.region}")
    client.delete_group(UserPoolId=user_pool_id, GroupName=group.GroupName)
    return True
