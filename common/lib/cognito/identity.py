import asyncio
import base64
import hashlib
import hmac
import logging
import random
import string
import urllib.parse
from datetime import date
from typing import Any, Dict, List, Union

import boto3
import sentry_sdk
from botocore.exceptions import ClientError
from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import ImmutableSandboxedEnvironment

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

ADMIN_GROUP_NAME = "noq_administrators"
CLIENT_SECRET_MASK = "********"
log = config.get_logger()


async def __get_google_provider(
    user_pool_id: str,
    identity_providers: Dict[str, List[Dict[str, Any]]],
    mask_secrets: bool,
    client=None,
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
            client_secret = identity_provider.get("ProviderDetails", {}).get(
                "client_secret"
            )
            google_provider = GoogleOIDCSSOIDPProvider(
                client_id=identity_provider.get("ProviderDetails", {}).get("client_id"),
                client_secret=CLIENT_SECRET_MASK if mask_secrets else client_secret,
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
    user_pool_id: str,
    identity_providers: Dict[str, List[Dict[str, Any]]],
    mask_secrets: bool,
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
            client_secret = identity_provider.get("ProviderDetails", {}).get(
                "client_secret"
            )
            oidc_provider = OIDCSSOIDPProvider(
                client_id=identity_provider.get("ProviderDetails", {}).get("client_id"),
                client_secret=CLIENT_SECRET_MASK if mask_secrets else client_secret,
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


def get_tenant_user_pool_region(tenant):
    return config.get_tenant_specific_key(
        "secrets.cognito.config.user_pool_region", tenant, config.region
    )


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


async def get_identity_providers(
    user_pool_id: str, client=None, mask_secrets: bool = False
) -> SSOIDPProviders:
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
        google=await __get_google_provider(
            user_pool_id, identity_providers, mask_secrets, client
        ),
        saml=await __get_saml_provider(user_pool_id, identity_providers, client),
        oidc=await __get_oidc_provider(user_pool_id, identity_providers, mask_secrets),
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
            updated_provider = getattr(id_provider, provider_type)
            if (
                hasattr(updated_provider, "client_secret")
                and updated_provider.client_secret == CLIENT_SECRET_MASK
            ):
                updated_provider.client_secret = current_provider.client_secret
                setattr(id_provider, provider_type, updated_provider)

            await disconnect_idp_from_app_client(
                user_pool_id, user_pool_client_id, current_provider, client=client
            )
            await delete_identity_provider(
                user_pool_id, current_provider, client=client
            )

    async def set_provider(identity_provider):
        log.info(
            f"Storing {identity_provider.provider_type} Identity Provider in Cognito in user pool {user_pool_id}"
        )
        provider_dict = identity_provider.dict()
        identity_provider_type = provider_dict.pop("provider_type")
        required = [
            k
            for k in identity_provider.required_fields()
            if k not in ["provider_name", "provider_type"]
        ]
        log.info(
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

    log.info(f"Created {len(responses)} IDP: {responses}")
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
        log_data = {
            "user_pool_id": user_pool_id,
            "user": user.Username,
            "group": group.GroupName,
        }
        try:
            await aio_wrapper(
                client.admin_add_user_to_group,
                UserPoolId=user_pool_id,
                Username=user.Username,
                GroupName=group.GroupName,
            )
        except client.exceptions.UserNotFoundException:
            log.warning({**log_data, "message": "User not found in user pool."})
            return False
        except client.exceptions.ResourceNotFoundException:
            log.warning({**log_data, "message": "Group not found in user pool."})
            return False
        except client.exceptions.ResourceConflictException:
            log.warning({**log_data, "message": "User already in group"})
            return False
        except Exception:
            log.error(
                {**log_data, "message": "Error assigning user to group"}, exc_info=True
            )
            sentry_sdk.capture_exception()
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
        log.warning(
            {
                "message": "User not found when attempting to remove user from group",
                "user": user.Username,
                "group": group.GroupName,
            }
        )
        return False
    except client.exceptions.ResourceNotFoundException:
        log.warning(
            {
                "message": "User is not assigned to group",
                "user": user.Username,
                "group": group.GroupName,
            }
        )
        return False
    except Exception as err:
        log.exception(
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


async def get_external_id(tenant, username):
    dig = hmac.new(
        str(tenant).encode("utf-8"),
        msg=str(username).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return dig


async def generate_dev_domain(dev_mode):
    suffix = "noq_localhost" if dev_mode else "noq_dev"

    for i in range(0, 25):
        tenant_id = random.randint(000000, 999999)
        dev_domain = f"dev-{tenant_id}_{suffix}"

        # check if the dev domain is available
        if not config.get_tenant_static_config_from_dynamo(dev_domain):
            return dev_domain


def generate_password() -> str:
    generated_password = [
        random.choice(string.punctuation) for _ in range(random.randint(1, 4))
    ]
    generated_password.extend(
        [random.choice(string.digits) for _ in range(random.randint(1, 4))]
    )
    generated_password.extend(
        [random.choice(string.ascii_uppercase) for _ in range(random.randint(4, 5))]
    )
    generated_password.extend(
        [random.choice(string.ascii_lowercase) for _ in range(random.randint(4, 5))]
    )
    random.shuffle(generated_password)
    return "".join(generated_password)


async def create_user_pool(noq_subdomain, domain_fqdn):
    cognito = boto3.client("cognito-idp", region_name=config.region)
    paginator = cognito.get_paginator("list_user_pools")
    response_iterator = paginator.paginate(
        PaginationConfig={"MaxItems": 60, "PageSize": 60}
    )
    user_pool_name = f"cloudumi_tenant_{noq_subdomain}"
    user_pool_already_exists = False
    for response in response_iterator:
        for user_pool in response["UserPools"]:
            if user_pool["Name"] == user_pool_name:
                user_pool_already_exists = True
                break
    if user_pool_already_exists:
        logging.warning(
            {"message": "User pool already exists", "user_pool": user_pool_name}
        )
        raise Exception("User Pool Already Exists")
    env = ImmutableSandboxedEnvironment(
        loader=FileSystemLoader("common/templates"),
        extensions=["jinja2.ext.loopcontrols"],
        autoescape=select_autoescape(),
    )
    cognito_invitation_message_template = env.get_template("cognito_invitation.j2")
    cognito_invitation_message = cognito_invitation_message_template.render(
        year=date.today().year, domain=domain_fqdn
    )
    cognito_email_subject = "Your temporary password for Noq"
    ses_source_arn = config.get("_global_.ses_notifications_sender_identity", None)
    if ses_source_arn is None:
        email_configuration = {"EmailSendingAccount": "COGNITO_DEFAULT"}
    else:
        email_configuration = {
            "EmailSendingAccount": "DEVELOPER",
            "SourceArn": config.get("_global_.ses_notifications_sender_identity", None),
        }
    response = cognito.create_user_pool(
        PoolName=user_pool_name,
        Schema=[
            {
                "Name": "sub",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": False,
                "Required": True,
                "StringAttributeConstraints": {"MinLength": "1", "MaxLength": "2048"},
            },
            {
                "Name": "name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "given_name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "family_name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "middle_name",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "nickname",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "preferred_username",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "profile",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "picture",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "website",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "email",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": True,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "email_verified",
                "AttributeDataType": "Boolean",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
            },
            {
                "Name": "gender",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "birthdate",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "10", "MaxLength": "10"},
            },
            {
                "Name": "zoneinfo",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "locale",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "phone_number",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "address",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
            },
            {
                "Name": "updated_at",
                "AttributeDataType": "Number",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "NumberAttributeConstraints": {"MinValue": "0"},
            },
            {
                "Name": "identities",
                "AttributeDataType": "String",
                "DeveloperOnlyAttribute": False,
                "Mutable": True,
                "Required": False,
                "StringAttributeConstraints": {},
            },
        ],
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": True,
                "RequireLowercase": True,
                "RequireNumbers": True,
                "RequireSymbols": True,
            }
        },
        AutoVerifiedAttributes=["email"],
        EmailConfiguration=email_configuration,
        UsernameAttributes=["email"],
        UserPoolTags={"tenant": noq_subdomain},
        AdminCreateUserConfig={
            "AllowAdminCreateUserOnly": True,
            "UnusedAccountValidityDays": 7,
            "InviteMessageTemplate": {
                "EmailMessage": cognito_invitation_message,
                "EmailSubject": cognito_email_subject,
            },
        },
        # TODO: Enable advanced security mode
        # UserPoolAddOns={
        #     'AdvancedSecurityMode': 'ENFORCED'
        # },
        UsernameConfiguration={"CaseSensitive": False},
        AccountRecoverySetting={
            "RecoveryMechanisms": [
                {"Priority": 1, "Name": "verified_email"},
            ]
        },
        VerificationMessageTemplate={
            "DefaultEmailOption": "CONFIRM_WITH_LINK",
        },
    )
    return response["UserPool"]["Id"]


async def create_user_pool_client(user_pool_id, dev_domain_url):
    cognito = boto3.client("cognito-idp", region_name=config.region)
    res = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName="noq_tenant",
        GenerateSecret=True,
        RefreshTokenValidity=1,
        AccessTokenValidity=60,
        IdTokenValidity=60,
        TokenValidityUnits={
            "AccessToken": "minutes",
            "IdToken": "minutes",
            "RefreshToken": "days",
        },
        ReadAttributes=[
            "address",
            "birthdate",
            "email",
            "email_verified",
            "family_name",
            "gender",
            "given_name",
            "locale",
            "middle_name",
            "name",
            "nickname",
            "phone_number",
            "phone_number_verified",
            "picture",
            "preferred_username",
            "profile",
            "updated_at",
            "website",
            "zoneinfo",
        ],
        WriteAttributes=[
            "address",
            "birthdate",
            "email",
            "family_name",
            "gender",
            "given_name",
            "locale",
            "middle_name",
            "name",
            "nickname",
            "phone_number",
            "picture",
            "preferred_username",
            "profile",
            "updated_at",
            "website",
            "zoneinfo",
        ],
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=[
            "ALLOW_CUSTOM_AUTH",
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_USER_SRP_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_ADMIN_USER_PASSWORD_AUTH",
        ],
        CallbackURLs=[
            f"{dev_domain_url}/auth",
            f"{dev_domain_url}/oauth2/idpresponse",
        ],
        LogoutURLs=[f"{dev_domain_url}", f"{dev_domain_url}/"],
        # DefaultRedirectURI=f'{dev_domain_url}/',
        AllowedOAuthFlows=[
            "code",
        ],
        AllowedOAuthScopes=[
            "email",
            "openid",
            "profile",
            "aws.cognito.signin.user.admin",
        ],
        AllowedOAuthFlowsUserPoolClient=True,
        PreventUserExistenceErrors="ENABLED",
        EnableTokenRevocation=True,
    )
    return res["UserPoolClient"]["ClientId"], res["UserPoolClient"]["ClientSecret"]


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


async def create_user_pool_domain(user_pool_id, user_pool_domain_name):
    cognito = boto3.client("cognito-idp", region_name=config.region)
    user_pool_domain = cognito.create_user_pool_domain(
        UserPoolId=user_pool_id, Domain=user_pool_domain_name
    )
    return user_pool_domain


class CognitoUserClient:
    """Encapsulates Amazon Cognito actions"""

    def __init__(
        self, user_pool_id, client_id=None, client_secret=None, cognito_idp_client=None
    ):
        """
        While client_id is optional, many CognitoUserClient methods require it.
            So, it is strongly recommended the client_id be provided
        :param user_pool_id: The ID of an existing Amazon Cognito user pool.
        :param client_id: The ID of a client application registered with the user pool.
        :param client_secret: The client secret, if the client has a secret.
        :param cognito_idp_client: A Boto3 Amazon Cognito Identity Provider client.
        """
        self.cognito_idp_client = cognito_idp_client or boto3.client(
            "cognito-idp", region_name=config.region
        )
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.client_secret = client_secret

        self.verify_user_pool_mfa_config()

    @classmethod
    def tenant_client(cls, tenant: str, cognito_idp_client=None):
        cognito_info = config.get_tenant_specific_key("secrets.cognito.config", tenant)
        region = get_tenant_user_pool_region(tenant)
        return cls(
            cognito_info["user_pool_id"],
            cognito_info["user_pool_client_id"],
            cognito_info["user_pool_client_secret"],
            cognito_idp_client or boto3.client("cognito-idp", region_name=region),
        )

    @staticmethod
    def get_totp_uri(username: str, secret_code: str, tenant: str):
        label = urllib.parse.urlencode(tenant.replace("_", "."))
        return f"otpauth://totp/{label}:{username}?secret={secret_code}&issuer={label}"

    def _secret_hash(self, username):
        """
        Calculates a secret hash from a user name and a client secret.

        :param username: The user name to use when calculating the hash.
        :return: The secret hash.
        """
        key = self.client_secret.encode()
        msg = bytes(username + self.client_id, "utf-8")
        secret_hash = base64.b64encode(
            hmac.new(key, msg, digestmod=hashlib.sha256).digest()
        ).decode()
        log.info("Made secret hash for %s: %s.", username, secret_hash)
        return secret_hash

    def resend_confirmation(self, username):
        """
        Prompts Amazon Cognito to resend an email with a new confirmation code.

        :param username: The name of the user who will receive the email.
        :return: Delivery information about where the email is sent.
        """
        try:
            kwargs = {"ClientId": self.client_id, "Username": username}
            if self.client_secret is not None:
                kwargs["SecretHash"] = self._secret_hash(username)
            response = self.cognito_idp_client.resend_confirmation_code(**kwargs)
            delivery = response["CodeDeliveryDetails"]
        except ClientError as err:
            log.error(
                "Couldn't resend confirmation to %s. Here's why: %s: %s",
                username,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return delivery

    async def start_sign_in(self, username, password):
        """
        Starts the sign-in process for a user by using administrator credentials.
        This method of signing in is appropriate for code running on a secure server.

        If the user pool is configured to require MFA and this is the first sign-in
        for the user, Amazon Cognito returns a challenge response to set up an
        MFA application. When this occurs, this function gets an MFA secret from
        Amazon Cognito and returns it to the caller.

        :param username: The name of the user to sign in.
        :param password: The user's password.
        :return: The result of the sign-in attempt. When sign-in is successful, this
                 returns an access token that can be used to get AWS credentials. Otherwise,
                 Amazon Cognito returns a challenge to set up an MFA application,
                 or a challenge to enter an MFA code from a registered MFA application.
        """
        try:
            kwargs = {
                "UserPoolId": self.user_pool_id,
                "ClientId": self.client_id,
                "AuthFlow": "ADMIN_USER_PASSWORD_AUTH",
                "AuthParameters": {"USERNAME": username, "PASSWORD": password},
            }
            if self.client_secret is not None:
                kwargs["AuthParameters"]["SECRET_HASH"] = self._secret_hash(username)
            response = await aio_wrapper(
                self.cognito_idp_client.admin_initiate_auth, **kwargs
            )
            if response.get("ChallengeName") == "MFA_SETUP":
                if (
                    "SOFTWARE_TOKEN_MFA"
                    in response["ChallengeParameters"]["MFAS_CAN_SETUP"]
                ):
                    response.update(
                        await self.get_mfa_secret(response["Session"]), tenant="noq"
                    )
                else:
                    raise RuntimeError(
                        "The user pool requires MFA setup, but the user pool is not "
                        "configured for TOTP MFA. This example requires TOTP MFA."
                    )
        except ClientError as err:
            log.error(
                "Couldn't start sign in for %s. Here's why: %s: %s",
                username,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            response.pop("ResponseMetadata", None)

        return response

    async def get_mfa_secret(
        self, username: str, tenant: str, session: str = None, access_token: str = None
    ):
        """
        Gets a token that can be used to associate an MFA application with the user.

        :param session: Session info returned from a previous call to initiate auth.
        :param access_token: access token created during the sign-in process.
        :return: An MFA token that can be used to set up an MFA application.
        """
        assert session or access_token
        try:
            if access_token:
                # Detect password sign-in without MFA
                associate_software_token = await aio_wrapper(
                    self.cognito_idp_client.associate_software_token,
                    AccessToken=access_token,
                )
                response = {
                    "SecretCode": associate_software_token["SecretCode"],
                    "AccessToken": access_token,
                }
            else:
                response = self.cognito_idp_client.associate_software_token(
                    Session=session
                )
        except ClientError as err:
            log.error(
                "Couldn't get MFA secret. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            response.pop("ResponseMetadata", None)
            response["TotpUri"] = self.get_totp_uri(
                username, response["SecretCode"], tenant
            )
            return response

    def verify_mfa(
        self,
        user_code: str,
        session: str = None,
        access_token: str = None,
        email: str = None,
    ):
        """
        Verify a new MFA application that is associated with a user.

        :param user_code: A code generated by the associated MFA application.
        :param session: Session information returned from a previous call to initiate authentication.
        :param access_token: Access Token returned from a previous call to initiate authentication.
        :param email: User email, required if access_token provided
        :return: Status that indicates whether the MFA application is verified.
        """
        assert session or access_token
        vst_params = {"UserCode": user_code}
        if session:
            vst_params["Session"] = session
        elif access_token:
            assert bool(email)
            vst_params["AccessToken"] = access_token

        try:
            response = self.cognito_idp_client.verify_software_token(**vst_params)
            if access_token:
                # Access Token is only used when after an MFA reset has completed so re-enable MFA
                self.update_user_mfa_status(email, True)
        except ClientError as err:
            log.error(
                "Couldn't verify MFA. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            response.pop("ResponseMetadata", None)

            return response

    def respond_to_mfa_challenge(self, username, session, mfa_code):
        """
        Responds to a challenge for an MFA code. This completes the second step of
        a two-factor sign-in. When sign-in is successful, it returns an access token
        that can be used to get AWS credentials from Amazon Cognito.

        :param username: The name of the user who is signing in.
        :param session: Session information returned from a previous call to initiate
                        authentication.
        :param mfa_code: A code generated by the associated MFA application.
        :return: The result of the authentication. When successful, this contains an
                 access token for the user.
        """
        try:
            kwargs = {
                "UserPoolId": self.user_pool_id,
                "ClientId": self.client_id,
                "ChallengeName": "SOFTWARE_TOKEN_MFA",
                "Session": session,
                "ChallengeResponses": {
                    "USERNAME": username,
                    "SOFTWARE_TOKEN_MFA_CODE": mfa_code,
                },
            }
            if self.client_secret is not None:
                kwargs["ChallengeResponses"]["SECRET_HASH"] = self._secret_hash(
                    username
                )
            response = self.cognito_idp_client.admin_respond_to_auth_challenge(**kwargs)
            auth_result = response["AuthenticationResult"]
        except ClientError as err:
            if err.response["Error"]["Code"] == "ExpiredCodeException":
                log.warning(
                    "Your MFA code has expired or has been used already. You might have "
                    "to wait a few seconds until your app shows you a new code."
                )
            else:
                log.error(
                    "Couldn't respond to mfa challenge for %s. Here's why: %s: %s",
                    username,
                    err.response["Error"]["Code"],
                    err.response["Error"]["Message"],
                )
                raise
        else:
            return auth_result

    async def reset_user_password(self, email, permanent: bool = False) -> str:
        # Change the user's password after enabling mfa
        generated_password = generate_password()
        self.cognito_idp_client.admin_set_user_password(
            UserPoolId=self.user_pool_id,
            Username=email,
            Password=generated_password,
            Permanent=permanent,
        )
        return generated_password

    async def create_init_user(self, email, username: str = None):
        # Only to be used for creating the first user in the tenant's Noq cognito user pool
        username = username or email
        await aio_wrapper(
            self.cognito_idp_client.create_group,
            UserPoolId=self.user_pool_id,
            GroupName=ADMIN_GROUP_NAME,
            Description="Noq Administrators",
        )

        user = await aio_wrapper(
            self.cognito_idp_client.admin_create_user,
            UserPoolId=self.user_pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email", "Value": email},
            ],
            DesiredDeliveryMediums=[
                "EMAIL",
            ],
        )

        await aio_wrapper(
            self.cognito_idp_client.admin_add_user_to_group,
            UserPoolId=self.user_pool_id,
            Username=username,
            GroupName=ADMIN_GROUP_NAME,
        )

        return {"user": user}

    def confirm_mfa_device(
        self,
        username,
        device_key,
        device_group_key,
        device_password,
        access_token,
        aws_srp,
    ):
        """
        Confirms an MFA device to be tracked by Amazon Cognito. When a device is
        tracked, its key and password can be used to sign in without requiring a new
        MFA code from the MFA application.

        :param username: The user that is associated with the device.
        :param device_key: The key of the device, returned by Amazon Cognito.
        :param device_group_key: The group key of the device, returned by Amazon Cognito.
        :param device_password: The password that is associated with the device.
        :param access_token: The user's access token.
        :param aws_srp: A class that helps with Secure Remote Password (SRP)
                        calculations. The scenario associated with this example uses
                        the warrant package.
        :return: True when the user must confirm the device. Otherwise, False. When
                 False, the device is automatically confirmed and tracked.
        """
        srp_helper = aws_srp.AWSSRP(
            username=username,
            password=device_password,
            pool_id="_",
            client_id=self.client_id,
            client_secret=None,
            client=self.cognito_idp_client,
        )
        device_and_pw = f"{device_group_key}{device_key}:{device_password}"
        device_and_pw_hash = aws_srp.hash_sha256(device_and_pw.encode("utf-8"))
        salt = aws_srp.pad_hex(aws_srp.get_random(16))
        x_value = aws_srp.hex_to_long(aws_srp.hex_hash(salt + device_and_pw_hash))
        verifier = aws_srp.pad_hex(pow(srp_helper.g, x_value, srp_helper.big_n))
        device_secret_verifier_config = {
            "PasswordVerifier": base64.standard_b64encode(
                bytearray.fromhex(verifier)
            ).decode("utf-8"),
            "Salt": base64.standard_b64encode(bytearray.fromhex(salt)).decode("utf-8"),
        }
        try:
            response = self.cognito_idp_client.confirm_device(
                AccessToken=access_token,
                DeviceKey=device_key,
                DeviceSecretVerifierConfig=device_secret_verifier_config,
            )
            user_confirm = response["UserConfirmationNecessary"]
        except ClientError as err:
            log.error(
                "Couldn't confirm mfa device %s. Here's why: %s: %s",
                device_key,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return user_confirm

    def update_user_mfa_status(self, username: str, enabled: bool):
        # RespondToAuthChallenge
        return self.cognito_idp_client.admin_set_user_mfa_preference(
            Username=username,
            UserPoolId=self.user_pool_id,
            SoftwareTokenMfaSettings={
                "Enabled": enabled,
                "PreferredMfa": enabled,
            },
        )

    def verify_user_pool_mfa_config(self):
        mfa_config_val = "OPTIONAL"
        user_pool_info = self.cognito_idp_client.get_user_pool_mfa_config(
            UserPoolId=self.user_pool_id
        )

        if user_pool_info.get("MfaConfiguration") != mfa_config_val:
            log.debug(
                {
                    "message": "Updating MFA Config",
                    "user_pool_id": self.user_pool_id,
                    "config_val": mfa_config_val,
                }
            )
            self.cognito_idp_client.set_user_pool_mfa_config(
                UserPoolId=self.user_pool_id,
                MfaConfiguration=mfa_config_val,
                SoftwareTokenMfaConfiguration={"Enabled": True},
            )

    def user_mfa_enabled(self, username: str) -> bool:
        try:
            user = self.cognito_idp_client.admin_get_user(
                UserPoolId=self.user_pool_id, Username=username
            )
        except Exception as exc:
            log.exception(exc)
            return False
        return bool(user.get("PreferredMfaSetting") == "SOFTWARE_TOKEN_MFA")

    async def list_users(self):
        """Get Cognito users and format as pydantic CognitoUser objects.

        Retrieves all cognito users and returns them in a list as CognitoUser
        objects.

        :return: a list of CognitoUser objects
        """
        users = list()
        response = await aio_wrapper(
            self.cognito_idp_client.list_users, UserPoolId=self.user_pool_id
        )
        users.extend(response.get("Users", []))
        next_token = response.get("NextToken")
        while next_token:
            response = await aio_wrapper(
                self.cognito_idp_client.list_users,
                UserPoolId=self.user_pool_id,
                NextToken=next_token,
            )
            users.extend(response.get("Users", []))
            next_token = response.get("NextToken")
        cognito_users = [CognitoUser(**x) for x in users]
        for cognito_user in cognito_users:
            cognito_user.Groups = [
                x.GroupName
                for x in await get_identity_user_groups(
                    self.user_pool_id, cognito_user, client=self.cognito_idp_client
                )
            ]
        return cognito_users

    async def delete_user(self, username: str) -> bool:
        """Delete a Cognito user.

        Uses the admin_delete_user functionality to delete a user from the
        Cognito database.

        :param username: The cognito user's username
        :return: true if successful
        """
        await aio_wrapper(
            self.cognito_idp_client.admin_delete_user,
            UserPoolId=self.user_pool_id,
            Username=username,
        )
        return True

    async def create_user(self, user: CognitoUser) -> CognitoUser:
        """Create a Cognito user account.

        Note: this account will delete an already existing user and recreate it. This
        uses the admin_create_user functionality, side-stepping the user sign up process.

        :param user: a CognitoUser object that is validated and describes the new use
        :return: an updated CognitoUser object that may contain additional info from AWS
        """
        current_users = await self.list_users()
        if user in [x for x in current_users]:
            await self.delete_user(user)
        delivery_mediums = list()
        if user.MFAOptions:
            delivery_mediums = [
                str(x.DeliveryMedium).split(".")[-1] for x in user.MFAOptions
            ]
        user_attributes = list()
        if user.Attributes:
            user_attributes = [dict(x) for x in user.Attributes]
        response = await aio_wrapper(
            self.cognito_idp_client.admin_create_user,
            UserPoolId=self.user_pool_id,
            Username=user.Username,
            UserAttributes=user_attributes,
            DesiredDeliveryMediums=delivery_mediums,
        )
        log.debug(
            {
                "message": "Created new user",
                "user_name": user.Username,
                "response": response,
                "user_pool_id": self.user_pool_id,
            }
        )
        user_update = CognitoUser(**response.get("User", {}))
        if user.Groups:
            log.info(f"Adding groups {user.Groups} to user {user.Username}")
            await create_identity_user_groups(
                self.user_pool_id,
                user_update,
                [CognitoGroup(GroupName=x) for x in user.Groups],
            )
        return user_update
