from unittest import IsolatedAsyncioTestCase

import boto3
import moto
import pytest
from asgiref.sync import async_to_sync

import common.lib.cognito.identity
from common.config import config
from common.lib.cognito import identity
from common.models import (
    CognitoGroup,
    CognitoUser,
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SSOIDPProviders,
)


@moto.mock_cognitoidp
@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("sts")
@pytest.mark.usefixtures("dynamodb")
class TestIdentity(IsolatedAsyncioTestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestIdentity, self).setUp()
        self.client = boto3.client("cognito-idp", region_name=config.region)
        self.pool_name = "test_pool"
        self.username = "test_user@gmail.com"
        self.groupname = "test_group"
        self.user = CognitoUser(Username=self.username)

        self.pool_id = async_to_sync(common.lib.cognito.identity.create_user_pool)(
            self.pool_name
        )
        self.client_id, self.client_secret = async_to_sync(
            common.lib.cognito.identity.create_user_pool_client
        )(
            self.pool_id,
            "test_domain",
        )

        self.client.create_identity_provider(
            UserPoolId=self.pool_id,
            ProviderName="SAML",
            ProviderType="SAML",
            ProviderDetails={
                "MetadataURL": "http://somewhere.yo.dawgs",
            },
        )
        self.client.create_group(
            UserPoolId=self.pool_id,
            GroupName=self.groupname,
            Description="test description",
        )
        self.user_client = identity.CognitoUserClient(self.pool_id)
        async_to_sync(self.user_client.create_user)(self.user)


    async def test_get_identity(self):
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert providers.saml.provider_name == "SAML"

    async def test_upsert_identity_provider_google(self):
        google_provider = GoogleOIDCSSOIDPProvider(
            client_id="test_id",
            client_secret="1234",
            authorize_scopes="scope1",
            provider_name="Google",
            provider_type="Google",
        )
        sso_provider = SSOIDPProviders(
            google=google_provider,
        )
        assert await identity.upsert_identity_provider(
            self.pool_id, self.client_id, sso_provider
        )
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.google
        assert providers.google.provider_name == "Google"
        assert providers.google.client_id == "test_id"

    async def test_upsert_identity_provider_saml(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="SAML",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(
            saml=saml_provider,
        )
        assert await identity.upsert_identity_provider(
            self.pool_id, self.client_id, sso_provider
        )
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert providers.saml.provider_name == "SAML"
        assert providers.saml.MetadataURL == "http://somewhere.over.the.rainbow"

    async def test_upsert_identity_provider_oidc_minimum(self):
        oidc_provider = OIDCSSOIDPProvider(
            client_id="test_id",
            client_secret="1234",
            attributes_request_method="test_request_method",
            oidc_issuer="test_oidc_sissuer",
            authorize_scopes="scope1",
            provider_name="OIDC",
            provider_type="OIDC",
        )
        sso_provider = SSOIDPProviders(
            oidc=oidc_provider,
        )
        assert await identity.upsert_identity_provider(
            self.pool_id, self.client_id, sso_provider
        )
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.oidc
        assert providers.oidc.provider_name == "OIDC"
        assert providers.oidc.client_id == "test_id"

    async def test_upsert_identity_provider_oidc_complete(self):
        oidc_provider = OIDCSSOIDPProvider(
            client_id="test_id",
            client_secret="1234",
            attributes_request_method="test_request_method",
            oidc_issuer="test_oidc_sissuer",
            authorize_scopes="scope1",
            authorize_url="http://authorize.this",
            token_url="http://tokenize.this",
            attributes_url="attributes...",
            jwks_uri="jwks://do.this",
            attributes_url_add_attributes="what.is.this?",
            provider_name="OIDC",
            provider_type="OIDC",
        )
        sso_provider = SSOIDPProviders(
            oidc=oidc_provider,
        )
        assert await identity.upsert_identity_provider(
            self.pool_id, self.client_id, sso_provider
        )
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.oidc
        assert providers.oidc.provider_name == "OIDC"
        assert providers.oidc.jwks_uri == "jwks://do.this"

    async def test_delete_identity_provider(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="SAML",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(saml=saml_provider)
        assert await identity.upsert_identity_provider(
            self.pool_id, self.client_id, sso_provider
        )
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert await identity.delete_identity_provider(self.pool_id, saml_provider)
        providers = await identity.get_identity_providers(self.pool_id)
        assert not providers.saml

    async def test_connect_idp_to_app_client(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="SAML",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(saml=saml_provider)
        assert await identity.upsert_identity_provider(
            self.pool_id, self.client_id, sso_provider
        )

        assert await identity.connect_idp_to_app_client(
            self.pool_id, self.client_id, saml_provider
        )
        app_clients = await identity.get_user_pool_client(self.pool_id, self.client_id)
        assert app_clients.get("SupportedIdentityProviders", []) == ["COGNITO", "SAML"]

    async def test_disconnect_idp_from_app_client(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="SAML",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(saml=saml_provider)
        assert await identity.upsert_identity_provider(
            self.pool_id, self.client_id, sso_provider
        )
        assert await identity.connect_idp_to_app_client(
            self.pool_id, self.client_id, saml_provider
        )
        app_clients = await identity.get_user_pool_client(self.pool_id, self.client_id)
        assert app_clients.get("SupportedIdentityProviders", []) == ["COGNITO", "SAML"]
        assert await identity.disconnect_idp_from_app_client(
            self.pool_id, self.client_id, saml_provider
        )
        app_clients = await identity.get_user_pool_client(self.pool_id, self.client_id)
        assert app_clients.get("SupportedIdentityProviders", []) == ["COGNITO"]

    async def test_get_identity_users(self):
        cognito_user = await self.user_client.list_users()
        user_dict: dict = cognito_user[0].dict()
        user_dict.pop("TemporaryPassword", None)
        for attr in user_dict.get("Attributes", []):
            if attr["Name"] == "email":
                user_dict["Username"] = attr["Value"]
                break
        self.assertEqual(user_dict["Username"], self.username)

    async def test_create_identity_user_sparse(self):
        user = CognitoUser(Username="new_user@gmail.com")
        user_update = await self.user_client.create_user(user)
        assert len(await self.user_client.list_users()) == 2
        self.client.admin_delete_user(
            UserPoolId=self.pool_id, Username=user_update.Username
        )
        assert len(await self.user_client.list_users()) == 1

    async def test_create_identity_user_complete(self):
        user = CognitoUser(
            UserPoolId=self.pool_id,
            Username="new_user@gmail.com",
            Attributes=[
                {
                    "Name": "some_name",
                    "Value": "some_value",
                },
            ],
            Enabled=True,
            MFAOptions=[{"DeliveryMedium": "SMS"}],
            UserStatus="COMPROMISED",
        )
        user_update = await self.user_client.create_user(user)
        assert len(await self.user_client.list_users()) == 2
        await self.user_client.delete_user(user_update.Username)
        assert len(await self.user_client.list_users()) == 1

    async def test_assigning_identity_user(self):
        group = CognitoGroup(GroupName=self.groupname, UserPoolId=self.pool_id)
        assert await identity.create_identity_user_groups(self.pool_id, self.user, [group])
        users = await self.user_client.list_users()
        for user in users:
            user_dict: dict = user.dict()
            user_dict.pop("TemporaryPassword", None)
            for attr in user_dict.get("Attributes", []):
                if attr["Name"] == "email":
                    user_dict["Username"] = attr["Value"]
                    break

            if user_dict["Username"] == self.username:
                assert user
                assert user.Groups
                assert len(user.Groups) == 1
                assert user.Groups[0] == self.groupname

    async def test_create_identity_user_with_groups(self):
        groups = ["group1", "group2"]
        username = "new_user@gmail.com"
        user = CognitoUser(Username=username, Groups=groups)
        for group in groups:
            assert await identity.create_identity_group(
                self.pool_id, CognitoGroup(GroupName=group)
            )
        assert await self.user_client.create_user(user)
        users = await self.user_client.list_users()
        for user in users:
            user_dict: dict = user.dict()
            user_dict.pop("TemporaryPassword", None)
            for attr in user_dict.get("Attributes", []):
                if attr["Name"] == "email":
                    user_dict["Username"] = attr["Value"]
                    break

            if user_dict["Username"] == username:
                assert user.Groups
                assert len([x for x in user.Groups if x in groups]) == len(groups)
                assert len(await self.user_client.list_users()) == 2
                self.client.admin_delete_user(
                    UserPoolId=self.pool_id, Username=user_dict["Username"]
                )
                for group in groups:
                    assert await identity.delete_identity_group(
                        self.pool_id, CognitoGroup(GroupName=group)
                    )
                assert len(await self.user_client.list_users()) == 1

    async def test_delete_identity_user(self):
        user = CognitoUser(Username="delete_user@gmail.com")
        await self.user_client.create_user(user)
        assert len(await self.user_client.list_users()) == 2
        await self.user_client.delete_user(user.Username)
        assert len(await self.user_client.list_users()) == 1

    async def test_get_identity_groups(self):
        get_identity_groups_call = await identity.get_identity_groups(self.pool_id)
        assert get_identity_groups_call[0].GroupName == self.groupname

    async def test_create_identity_group_sparse(self):
        group = CognitoGroup(UserPoolId=self.pool_id, GroupName="new_group")
        group_update = await identity.create_identity_group(self.pool_id, group)
        assert len(await identity.get_identity_groups(self.pool_id)) == 2
        self.client.delete_group(
            UserPoolId=self.pool_id, GroupName=group_update.GroupName
        )
        assert len(await identity.get_identity_groups(self.pool_id)) == 1

    async def test_create_identity_group_complete(self):
        group = CognitoGroup(
            UserPoolId=self.pool_id,
            GroupName="new_group",
            Description="a new group",
            RoleArn="aws:iam:::::",
        )
        group_update = await identity.create_identity_group(self.pool_id, group)
        assert len(await identity.get_identity_groups(self.pool_id)) == 2
        self.client.delete_group(
            UserPoolId=self.pool_id, GroupName=group_update.GroupName
        )
        assert len(await identity.get_identity_groups(self.pool_id)) == 1

    async def test_delete_identity_group(self):
        group = CognitoGroup(UserPoolId=self.pool_id, GroupName="delete_user")
        _ = await identity.create_identity_group(self.pool_id, group)
        assert len(await identity.get_identity_groups(self.pool_id)) == 2
        await identity.delete_identity_group(self.pool_id, group)
        assert len(await identity.get_identity_groups(self.pool_id)) == 1
