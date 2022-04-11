from unittest import IsolatedAsyncioTestCase

import boto3
import moto
import pytest

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
class TestIdentity(IsolatedAsyncioTestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestIdentity, self).setUp()
        self.client = boto3.client("cognito-idp", region_name=config.region)
        self.pool_name = "test_pool"
        self.pool_response = self.client.create_user_pool(PoolName=self.pool_name)
        self.pool_id = self.pool_response.get("UserPool", {}).get("Id")
        self.user_pool_client = self.client.create_user_pool_client(
            UserPoolId=self.pool_id,
            ClientName="test_client",
        ).get("UserPoolClient", {})

        self.username = "test_user"
        self.temp_pass = "test123"
        self.groupname = "test_group"
        self.client.create_identity_provider(
            UserPoolId=self.pool_id,
            ProviderName="test_provider",
            ProviderType="SAML",
            ProviderDetails={
                "MetadataURL": "http://somewhere.yo.dawgs",
            },
        )
        self.client.admin_create_user(
            UserPoolId=self.pool_id,
            Username=self.username,
            TemporaryPassword=self.temp_pass,
        )
        self.client.create_group(
            UserPoolId=self.pool_id,
            GroupName=self.groupname,
            Description="test description",
        )

    async def test_get_identity(self):
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert providers.saml.provider_name == "test_provider"

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
            self.pool_id, self.user_pool_client["ClientId"], sso_provider
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
            self.pool_id, self.user_pool_client["ClientId"], sso_provider
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
            self.pool_id, self.user_pool_client["ClientId"], sso_provider
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
            self.pool_id, self.user_pool_client["ClientId"], sso_provider
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
            self.pool_id, self.user_pool_client["ClientId"], sso_provider
        )
        providers = await identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert await identity.delete_identity_provider(self.pool_id, saml_provider)
        providers = await identity.get_identity_providers(self.pool_id)
        assert not providers.saml

    async def test_connect_idp_to_app_client(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="Saml",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(saml=saml_provider)
        assert await identity.upsert_identity_provider(
            self.pool_id, self.user_pool_client["ClientId"], sso_provider
        )

        assert await identity.connect_idp_to_app_client(
            self.pool_id, self.user_pool_client.get("ClientId"), saml_provider
        )
        app_clients = await identity.get_user_pool_client(
            self.pool_id, self.user_pool_client["ClientId"]
        )
        assert app_clients.get("UserPoolClient", {}).get(
            "SupportedIdentityProviders", []
        ) == ["Saml"]

    async def test_disconnect_idp_from_app_client(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="Saml",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(saml=saml_provider)
        assert await identity.upsert_identity_provider(
            self.pool_id, self.user_pool_client["ClientId"], sso_provider
        )
        assert await identity.connect_idp_to_app_client(
            self.pool_id, self.user_pool_client.get("ClientId"), saml_provider
        )
        app_clients = await identity.get_user_pool_client(
            self.pool_id, self.user_pool_client.get("ClientId")
        )
        assert app_clients.get("UserPoolClient", {}).get(
            "SupportedIdentityProviders", []
        ) == ["Saml"]
        assert await identity.disconnect_idp_from_app_client(
            self.pool_id, self.user_pool_client.get("ClientId"), saml_provider
        )
        app_clients = await identity.get_user_pool_client(
            self.pool_id, self.user_pool_client.get("ClientId")
        )
        assert (
            app_clients.get("UserPoolClient", {}).get("SupportedIdentityProviders", [])
            == []
        )

    async def test_get_identity_users(self):
        cognito_user = await identity.get_identity_users(self.pool_id)
        self.assertEqual(cognito_user[0].Username, self.username)

    async def test_create_identity_user_sparse(self):
        user = CognitoUser(UserPoolId=self.pool_id, Username="new_user")
        user_update = await identity.create_identity_user(self.pool_id, user)
        assert len(await identity.get_identity_users(self.pool_id)) == 2
        self.client.admin_delete_user(
            UserPoolId=self.pool_id, Username=user_update.Username
        )
        assert len(await identity.get_identity_users(self.pool_id)) == 1

    async def test_create_identity_user_complete(self):
        user = CognitoUser(
            UserPoolId=self.pool_id,
            Username="new_user",
            Attributes=[
                {
                    "Name": "some_name",
                    "Value": "some_value",
                },
            ],
            Enabled=True,
            TemporaryPassword=self.temp_pass,
            MFAOptions=[{"DeliveryMedium": "SMS"}],
            UserStatus="COMPROMISED",
        )
        user_update = await identity.create_identity_user(self.pool_id, user)
        assert len(await identity.get_identity_users(self.pool_id)) == 2
        self.client.admin_delete_user(
            UserPoolId=self.pool_id, Username=user_update.Username
        )
        assert len(await identity.get_identity_users(self.pool_id)) == 1

    async def test_assigning_identity_user(self):
        user = CognitoUser(UserPoolId=self.pool_id, Username=self.username)
        group = CognitoGroup(GroupName=self.groupname, UserPoolId=self.pool_id)
        assert await identity.create_identity_user_groups(self.pool_id, user, [group])
        users = await identity.get_identity_users(self.pool_id)
        updated_user = [x for x in users if x.Username == self.username][0]
        assert updated_user
        assert updated_user.Groups
        assert len(updated_user.Groups) == 1
        assert updated_user.Groups[0] == self.groupname

    async def test_create_identity_user_with_groups(self):
        groups = ["group1", "group2"]
        user = CognitoUser(UserPoolId=self.pool_id, Username="new_user", Groups=groups)
        for group in groups:
            assert await identity.create_identity_group(
                self.pool_id, CognitoGroup(GroupName=group)
            )
        assert await identity.create_identity_user(self.pool_id, user)
        user_update = [
            x
            for x in await identity.get_identity_users(self.pool_id)
            if x.Username == "new_user"
        ][0]
        assert user_update.Groups
        assert len([x for x in user_update.Groups if x in groups]) == len(groups)
        assert len(await identity.get_identity_users(self.pool_id)) == 2
        self.client.admin_delete_user(
            UserPoolId=self.pool_id, Username=user_update.Username
        )
        for group in groups:
            assert await identity.delete_identity_group(
                self.pool_id, CognitoGroup(GroupName=group)
            )
        assert len(await identity.get_identity_users(self.pool_id)) == 1

    async def test_delete_identity_user(self):
        user = CognitoUser(UserPoolId=self.pool_id, Username="delete_user")
        _ = await identity.create_identity_user(self.pool_id, user)
        assert len(await identity.get_identity_users(self.pool_id)) == 2
        await identity.delete_identity_user(self.pool_id, user)
        assert len(await identity.get_identity_users(self.pool_id)) == 1

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
