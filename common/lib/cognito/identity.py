from typing import Any, Dict, List, Union

import boto3

from common.config import config
from common.models import (
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SSOIDPProviders,
)

LOG = config.get_logger()


def get_identity_providers(user_pool_id: str) -> List[Dict[str, Any]]:
    """Get all identity providers.

    Queries AWS Cognito IDP for all identity providers, automatically paginates

    :param user_pool_id: ensure this is the user pool ID not the user pool name!
    :return: a list of dictionaries, each of which has the format
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
    identity_providers = client.list_identity_providers(UserPoolId=user_pool_id) or []
    next_token = identity_providers.get("NextToken")
    if next_token:
        identity_providers.append(
            client.list_identity_providers(
                UserPoolId=user_pool_id, NextToken=next_token
            )
        )
    return identity_providers.get("Providers", [])


def upsert_identity_provider(user_pool_id: str, id_provider: SSOIDPProviders) -> bool:
    """Inserts or updates a identity provider.

    Some identity providers, such as SAML and possibly OIDC, can have multiple provider names, while
    Google seems to be limited to one as per experiments on the AWS UI

    :param user_pool_id: ensure this is the user pool ID not the user pool name!
    :param id_provider: the pydantic model SSOIDPProviders with one of the groups filled out (either google, saml or oidc)
    :return: True if the operation is successful - currently always returns true or raises an exception
    """
    client = boto3.client("cognito-idp", region_name=config.region)
    identity_provider_dict = dict()
    identity_provider_type = ""
    responses = list()

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
        provider_required = ["metadata_url"]
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
