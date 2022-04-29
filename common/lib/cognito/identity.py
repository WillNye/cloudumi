import asyncio
from typing import Any, Dict, List, Union

import boto3

from common.config import config
from common.lib.asyncio import aio_wrapper
from common.models import (
    CognitoGroup,
    CognitoUser,
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SSOIDPProviders,
)

LOG = config.get_logger()


async def __get_google_provider(
    user_pool_id: str, identity_providers: Dict[str, List[Dict[str, Any]]], client=None
) -> Union[GoogleOIDCSSOIDPProvider, None]:
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    google_provider = None
    google_provider_names = [
        x.get("ProviderName")
        for x in identity_providers
        if x.get("ProviderType") == "Google"
    ]
    if google_provider_names:
        identity_provider_call = await aio_wrapper(
            client.describe_identity_provider,
            UserPoolId=user_pool_id,
            ProviderName=google_provider_names[0],
        )
        identity_provider = identity_provider_call.get("IdentityProvider", {})
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


async def __get_saml_provider(
    user_pool_id: str, identity_providers: Dict[str, List[Dict[str, Any]]], client=None
) -> Union[SamlOIDCSSOIDPProvider, None]:
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    saml_provider = None
    saml_provider_names = [
        x.get("ProviderName")
        for x in identity_providers
        if x.get("ProviderType") == "SAML"
    ]
    if saml_provider_names:
        identity_provider_call = await aio_wrapper(
            client.describe_identity_provider,
            UserPoolId=user_pool_id,
            ProviderName=saml_provider_names[0],
        )
        identity_provider = identity_provider_call.get("IdentityProvider", {})
        if identity_provider:
            saml_provider = SamlOIDCSSOIDPProvider(
                MetadataURL=identity_provider.get("ProviderDetails", {}).get(
                    "MetadataURL"
                ),
                provider_name=identity_provider.get("ProviderName"),
                provider_type=identity_provider.get("ProviderType"),
            )
    return saml_provider


async def __get_oidc_provider(
    user_pool_id: str, identity_providers: Dict[str, List[Dict[str, Any]]], client=None
) -> Union[OIDCSSOIDPProvider, None]:
    client = await aio_wrapper(boto3.client, "cognito-idp", region_name=config.region)
    oidc_provider = None
    oidc_provider_names = [
        x.get("ProviderName")
        for x in identity_providers
        if x.get("ProviderType") == "OIDC"
    ]
    if oidc_provider_names:
        identity_provider_call = await aio_wrapper(
            client.describe_identity_provider,
            UserPoolId=user_pool_id,
            ProviderName=oidc_provider_names[0],
        )
        identity_provider = identity_provider_call.get("IdentityProvider", {})
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


async def get_user_pool_client_id(
    user_pool_id: str, client_name: str, client=None
) -> str:
    """Get the user pool client ID for a given client name.

    :param user_pool_id: the user pool ID
    :param client_name: the client name
    :return: the user pool ID
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    response = await aio_wrapper(client.list_user_pool_clients, UserPoolId=user_pool_id)
    for client in response.get("UserPoolClients", []):
        if client.get("ClientName") == client_name:
            return client.get("ClientId")
    next_token = response.get("NextToken")
    while next_token:
        response = await aio_wrapper(
            client.list_user_pool_clients, UserPoolId=user_pool_id, NextToken=next_token
        )
        for client in response.get("UserPoolClients", []):
            if client.get("ClientName") == client_name:
                return client.get("ClientId")
        next_token = response.get("NextToken")
    raise Exception(f"Could not find user pool ID for client {client_name}")


async def get_user_pool_client(user_pool_id: str, client_id: str, client=None) -> dict:
    """Get a specific client from a user pool.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param client_id: the client ID to get
    :param client: The boto3 client to use when interfacing with AWS
    :return: the client object
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    response = await aio_wrapper(
        client.describe_user_pool_client, UserPoolId=user_pool_id, ClientId=client_id
    )
    return response.get("UserPoolClient", {})


async def update_user_pool_client(boto_conn, user_pool: dict):
    """Sanitizes the request(user_pool) data and updates the user pool client in boto3"""
    user_pool.pop("ClientSecret", None)
    user_pool.pop("CreationDate", None)
    user_pool.pop("LastModifiedDate", None)
    await aio_wrapper(boto_conn.update_user_pool_client, **user_pool)


async def connect_idp_to_app_client(
    user_pool_id: str,
    client_id: str,
    idp: Union[GoogleOIDCSSOIDPProvider, SamlOIDCSSOIDPProvider, OIDCSSOIDPProvider],
    client=None,
) -> bool:
    """Connects the IDP to the app client.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param client_id: the client ID of the app client
    :param client: The boto3 client to use when interfacing with AWS
    :return: true if successful, currently always returns true
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    user_pool = await get_user_pool_client(user_pool_id, client_id, client=client)
    user_pool_supported_idp = user_pool.get("SupportedIdentityProviders", [])

    if idp.provider_name not in user_pool_supported_idp:
        user_pool_supported_idp.append(idp.provider_name)
        user_pool["SupportedIdentityProviders"] = user_pool_supported_idp
        await update_user_pool_client(client, user_pool)
    return True


async def disconnect_idp_from_app_client(
    user_pool_id: str,
    client_id: str,
    idp: Union[GoogleOIDCSSOIDPProvider, SamlOIDCSSOIDPProvider, OIDCSSOIDPProvider],
    client=None,
) -> bool:
    """Disconnect an IDP from the app client.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param client_id: the client ID of the app client
    :param idp: one of the NOQ internal identity provider objects
    :param client: The boto3 client to use when interfacing with AWS
    :return: reflects that the desired state is reached, meaning that the idp is not connected to the app client
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    user_pool = await get_user_pool_client(user_pool_id, client_id, client=client)
    user_pool_supported_idp = user_pool.get("SupportedIdentityProviders")
    if not user_pool_supported_idp:
        return True
    if idp.provider_name in user_pool_supported_idp:
        user_pool_supported_idp.remove(idp.provider_name)
        user_pool["SupportedIdentityProviders"] = user_pool_supported_idp
        await update_user_pool_client(client, user_pool)
    return True


async def get_identity_providers(user_pool_id: str, client=None) -> SSOIDPProviders:
    """Get all identity providers.

    Queries AWS Cognito IDP for all identity providers, automatically paginates; here is the thing though,
    it only returns the first of each Google, Saml and Oidc providers. This is intentional because that
    is all we support setting at the moment. This is also why this is returning a SSOIDPProviders object
    to retain consistency within NOQ.

    :param user_pool_id: ensure this is the user pool ID not the user pool name!
    :param client: The boto3 client to use when interfacing with AWS
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
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    response = await aio_wrapper(
        client.list_identity_providers, UserPoolId=user_pool_id
    )
    identity_providers = list()
    identity_providers.extend(response.get("Providers", []))
    next_token = response.get("NextToken")
    while next_token:
        response = await aio_wrapper(
            client.list_identity_providers,
            UserPoolId=user_pool_id,
            NextToken=next_token,
        )
        identity_providers.extend(response.get("Providers", []))
        next_token = response.get("NextToken")

    return SSOIDPProviders(
        google=await __get_google_provider(user_pool_id, identity_providers, client),
        saml=await __get_saml_provider(user_pool_id, identity_providers, client),
        oidc=await __get_oidc_provider(user_pool_id, identity_providers, client),
    )


async def upsert_identity_provider(
    user_pool_id: str,
    user_pool_client_id: str,
    id_provider: SSOIDPProviders,
    client=None,
) -> bool:
    """Inserts or updates an identity provider.

    Some identity providers, such as SAML and possibly OIDC, can have multiple provider names, while
    Google seems to be limited to one as per experiments on the AWS UI

    Upsert is a destructive operation now, because NOQ only supports one of each type of provider; however,
    Cognito supports setting multiple SAML and OIDC providers.

    So we first check if a provider is already set and delete it. We check Google as well for consistency,
    although **at this time** AWS only allows one Google provider. This is a defensive programming measure
    to avoid weird bugs later.

    :param user_pool_id: ensure this is the user pool ID not the user pool name!
    :param user_pool_client_id: ensure this is the user pool client ID
    :param id_provider: the pydantic model SSOIDPProviders with one of the groups filled out (either google, saml or oidc)
    :param client: The boto3 client to use when interfacing with AWS
    :return: True if the operation is successful - currently always returns true or raises an exception
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    responses = list()

    current_providers = await get_identity_providers(user_pool_id, client)
    supported_providers = list(SSOIDPProviders.__dict__["__fields__"].keys())
    for provider_type in supported_providers:
        # If a request is being made to set an already defined provider, remove the existing provider
        if getattr(id_provider, provider_type) and (
            current_provider := getattr(current_providers, provider_type)
        ):
            await disconnect_idp_from_app_client(
                user_pool_id, user_pool_client_id, current_provider, client=client
            )
            await delete_identity_provider(
                user_pool_id, current_provider, client=client
            )

    async def set_provider(identity_provider):
        LOG.info(
            f"Storing {identity_provider.provider_type} Identity Provider in Cognito in user pool {user_pool_id}"
        )
        provider_dict = identity_provider.dict()
        identity_provider_type = provider_dict.pop("provider_type")
        required = [
            k
            for k in identity_provider.required_fields()
            if k not in ["provider_name", "provider_type"]
        ]
        LOG.info(
            f"Using {required} to create_identity_provider in Cognito with type {provider_type}"
        )

        response = await aio_wrapper(
            client.create_identity_provider,
            UserPoolId=user_pool_id,
            ProviderName=identity_provider_type,
            ProviderType=identity_provider_type,
            ProviderDetails={
                field: provider_dict.get(field)
                for field in required
                if provider_dict.get(field)
            },
        )
        await connect_idp_to_app_client(
            user_pool_id, user_pool_client_id, identity_provider, client=client
        )
        return response

    for provider_type in supported_providers:
        if provider := getattr(id_provider, provider_type):
            responses.append(await set_provider(provider))

    LOG.info(f"Created {len(responses)} IDP: {responses}")
    return True


async def delete_identity_provider(
    user_pool_id: str,
    id_provider: Union[
        GoogleOIDCSSOIDPProvider, SamlOIDCSSOIDPProvider, OIDCSSOIDPProvider
    ],
    client=None,
) -> bool:
    """Delete an identity provider given a specific pydantic identity model.

    :param user_pool_id: ensure this is the user pool ID not the user pool name
    :param id_provider: any id provider model object - see union typing hint
    :param client: The boto3 client to use when interfacing with AWS
    :return: true if successful, currently always returns true
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    await aio_wrapper(
        client.delete_identity_provider,
        UserPoolId=user_pool_id,
        ProviderName=id_provider.provider_name,
    )
    return True


async def get_identity_user_groups(
    user_pool_id: str, user: CognitoUser, client=None
) -> List[CognitoGroup]:
    """Get the group assignments for a user pool.

    :param user_pool_id: the user pool ID
    :param user: the user for which to extract group assignments
    :param client: The boto3 client to use when interfacing with AWS
    :return: a list of dictionaries representing the group assignments
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    groups = list()
    response = await aio_wrapper(
        client.admin_list_groups_for_user,
        Username=user.Username,
        UserPoolId=user_pool_id,
    )
    groups.extend([CognitoGroup(**x) for x in response.get("Groups", [])])
    next_token = response.get("NextToken")
    while next_token:
        response = await aio_wrapper(
            client.admin_list_groups_for_user,
            Username=user.Username,
            UserPoolId=user_pool_id,
        )
        groups.extend([CognitoGroup(**x) for x in response.get("Groups", [])])
        next_token = response.get("NextToken")
    return groups


async def get_identity_users(user_pool_id: str, client=None) -> List[CognitoUser]:
    """Get Cognito users and format as pydantic CognitoUser objects.

    Retrieves all cognito users and returns them in a list as CognitoUser
    objects.

    :param user_pool_id: the current user pool id
    :param client: The boto3 client to use when interfacing with AWS
    :return: a list of CognitoUser objects
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    users = list()
    response = await aio_wrapper(client.list_users, UserPoolId=user_pool_id)
    users.extend(response.get("Users", []))
    next_token = response.get("NextToken")
    while next_token:
        response = await aio_wrapper(
            client.list_users, UserPoolId=user_pool_id, NextToken=next_token
        )
        users.extend(response.get("Users", []))
        next_token = response.get("NextToken")
    cognito_users = [CognitoUser(**x) for x in users]
    for cognito_user in cognito_users:
        cognito_user.Groups = [
            x.GroupName
            for x in await get_identity_user_groups(
                user_pool_id, cognito_user, client=client
            )
        ]
    return cognito_users


async def create_identity_user(
    user_pool_id: str, user: CognitoUser, client=None
) -> CognitoUser:
    """Create a Cognito user account.

    Note: this account will delete an already existing user and recreate it. This
    uses the admin_create_user functionality, side-stepping the user sign up process.

    :param user_pool_id: the id of the user pool that should have the new user
    :param user: a CognitoUser object that is validated and describes the new use
    :param client: The boto3 client to use when interfacing with AWSr
    :return: an updated CognitoUser object that may contain additional info from AWS
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    current_users = await get_identity_users(user_pool_id, client=client)
    if user in [x for x in current_users]:
        await delete_identity_user(user_pool_id, user, client=client)
    delivery_mediums = list()
    if user.MFAOptions:
        delivery_mediums = [
            str(x.DeliveryMedium).split(".")[-1] for x in user.MFAOptions
        ]
    user_attributes = list()
    if user.Attributes:
        user_attributes = [dict(x) for x in user.Attributes]
    response = await aio_wrapper(
        client.admin_create_user,
        UserPoolId=user_pool_id,
        Username=user.Username,
        UserAttributes=user_attributes,
        DesiredDeliveryMediums=delivery_mediums,
    )
    user_update = CognitoUser(**response.get("User", {}))
    if user.Groups:
        LOG.info(f"Adding groups {user.Groups} to user {user.Username}")
        await create_identity_user_groups(
            user_pool_id, user_update, [CognitoGroup(GroupName=x) for x in user.Groups]
        )
    return user_update


async def delete_identity_user(
    user_pool_id: str, user: CognitoUser, client=None
) -> bool:
    """Delete a Cognito user.

    Uses the admin_delete_user functionality to delete a user from the
    Cognito database.

    :param user_pool_id: the id of the user pool from which to delete the user
    :param user: a CognitoUser object that describes the user
    :param client: The boto3 client to use when interfacing with AWS
    :return: true if successful
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    await aio_wrapper(
        client.admin_delete_user, UserPoolId=user_pool_id, Username=user.Username
    )
    return True


async def create_identity_user_groups(
    user_pool_id: str, user: CognitoUser, groups: List[CognitoGroup], client=None
) -> bool:
    """Assign a user to a group.

    :param user_pool_id: the id of the user pool from which to delete the user
    :param user: a CognitoUser object that describes the user
    :param groups: a list of CognitoGroup objects that describe the groups to which the user should be added
    :return: true if successful
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    for group in groups:
        try:
            await aio_wrapper(
                client.admin_add_user_to_group,
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


async def remove_identity_user_group(
    user_pool_id: str, user: CognitoUser, group: CognitoGroup, client=None
) -> bool:
    """Remove a user from a group.

    :param user_pool_id: the id of the user pool
    :param user: a CognitoUser object that describes the user
    :param group: A CognitoGroup object that describe the group to which the user should be removed
    :param client: The boto3 client to use when interfacing with AWS
    :return: true if successful
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)

    try:
        await aio_wrapper(
            client.admin_remove_user_from_group,
            UserPoolId=user_pool_id,
            Username=user.Username,
            GroupName=group.GroupName,
        )
    except client.exceptions.UserNotFoundException:
        LOG.warning(
            {
                "message": "User not found when attempting to remove user from group",
                "user": user.Username,
                "group": group.GroupName,
            }
        )
        return False
    except client.exceptions.ResourceNotFoundException:
        LOG.warning(
            {
                "message": "User is not assigned to group",
                "user": user.Username,
                "group": group.GroupName,
            }
        )
        return False
    except Exception as err:
        LOG.exception(
            {
                "message": "Error removing user from group",
                "user": user.Username,
                "group": group.GroupName,
                "error": repr(err),
            }
        )
        return False
    else:
        return True


async def upsert_identity_user_group(
    user_pool_id: str, user: CognitoUser, client=None
) -> bool:
    """Removes old identity groups and creates ones that don't exist for the provided cognito user

    :param user_pool_id: the id of the user pool from which to delete the user
    :param user: a CognitoUser object that describes the user
    :param client: The boto3 client to use when interfacing with AWS
    :return: true if successful
    """
    existing_groups = await get_identity_user_groups(user_pool_id, user, client=client)

    await asyncio.gather(
        *[
            remove_identity_user_group(user_pool_id, user, group, client=client)
            for group in existing_groups
            if group not in user.Groups
        ]
    )

    return await create_identity_user_groups(
        user_pool_id,
        user,
        [group for group in user.Groups if group not in existing_groups],
        client=client,
    )


async def get_identity_group(
    user_pool_id: str, group_name: str, client=None
) -> CognitoGroup:
    """Retrieve a single Cognito group.

    :param user_pool_id: the id of the user pool
    :param group_name: the name of the group to retrieve
    :param client: The boto3 client to use when interfacing with AWS
    :return: The requested CognitoGroup object
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    response = await aio_wrapper(
        client.get_group, UserPoolId=user_pool_id, GroupName=group_name
    )
    return CognitoGroup(**response.get("Group", {}))


async def get_identity_groups(user_pool_id: str, client=None) -> List[CognitoGroup]:
    """Get Cognito groups.

    :param user_pool_id: the id of the user pool from which to get groups
    :param client: The boto3 client to use when interfacing with AWS
    :return: a list of CognitoGroup objects
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    groups = list()
    response = await aio_wrapper(client.list_groups, UserPoolId=user_pool_id)
    groups.extend(response.get("Groups", []))
    next_token = response.get("NextToken")
    while next_token:
        response = await aio_wrapper(
            client.list_groups, UserPoolId=user_pool_id, NextToken=next_token
        )
        groups.extend(response.get("Groups", []))
        next_token = response.get("NextToken")
    return [CognitoGroup(**x) for x in groups]


async def create_identity_group(
    user_pool_id: str, group: CognitoGroup, client=None
) -> CognitoGroup:
    """Create a Cognito group.

    :param user_pool_id: the id of the user pool in which to create the group
    :param group: a CognitoGroup object that describes the group
    :param client: The boto3 client to use when interfacing with AWS
    :return: an updated group object that may contain additional information from AWS
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    current_groups = await get_identity_groups(user_pool_id, client=client)
    if group in [x for x in current_groups]:
        await delete_identity_group(user_pool_id, group, client=client)
    response = await aio_wrapper(
        client.create_group,
        UserPoolId=user_pool_id,
        GroupName=group.GroupName,
        Description=group.Description,
    )
    group_update = CognitoGroup(**response.get("Group", {}))
    return group_update


async def update_identity_group(
    user_pool_id: str, group: CognitoGroup, client=None
) -> CognitoGroup:
    """Update a Cognito group

    :param user_pool_id: the id of the user pool that contains the group to be updated
    :param group: a CognitoGroup object that describes the group
    :param client: The boto3 client to use when interfacing with AWS
    :return: The updated cognito group
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    response = await aio_wrapper(
        client.update_group,
        UserPoolId=user_pool_id,
        GroupName=group.GroupName,
        Description=group.Description,
    )
    return CognitoGroup(**response.get("Group", {}))


async def delete_identity_group(
    user_pool_id: str, group: CognitoGroup, client=None
) -> bool:
    """Delete a Cognito group

    :param user_pool_id: the id of the user pool that contains the group to be deleted
    :param group: a CognitoGroup object that describes the group
    :param client: The boto3 client to use when interfacing with AWS
    :return: true if successful
    """
    if not client:
        client = boto3.client("cognito-idp", region_name=config.region)
    await aio_wrapper(
        client.delete_group, UserPoolId=user_pool_id, GroupName=group.GroupName
    )
    return True
