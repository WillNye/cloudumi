from unittest import TestCase

import boto3
import moto

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
class TestIdentity(TestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestIdentity, self).setUp()
        self.client = boto3.client("cognito-idp")
        self.pool_name = "test_pool"
        self.pool_response = self.client.create_user_pool(PoolName=self.pool_name)
        self.pool_id = self.pool_response.get("UserPool", {}).get("Id")
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

    def test_get_identity(self):
        providers = identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert providers.saml.provider_name == "test_provider"

    def test_upsert_identity_provider_google(self):
        google_provider = GoogleOIDCSSOIDPProvider(
            client_id="test_id",
            client_secret="1234",
            authorize_scopes="scope1",
            provider_name="GoogleIDP",
            provider_type="Google",
        )
        sso_provider = SSOIDPProviders(
            google=google_provider,
        )
        assert identity.upsert_identity_provider(self.pool_id, sso_provider)
        providers = identity.get_identity_providers(self.pool_id)
        assert providers.google
        assert providers.google.provider_name == "GoogleIDP"
        assert providers.google.client_id == "test_id"

    def test_upsert_identity_provider_saml(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="test_provider",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(
            saml=saml_provider,
        )
        assert identity.upsert_identity_provider(self.pool_id, sso_provider)
        providers = identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert providers.saml.provider_name == "test_provider"
        assert providers.saml.MetadataURL == "http://somewhere.over.the.rainbow"

    def test_upsert_identity_provider_oidc_minimum(self):
        oidc_provider = OIDCSSOIDPProvider(
            client_id="test_id",
            client_secret="1234",
            attributes_request_method="test_request_method",
            oidc_issuer="test_oidc_sissuer",
            authorize_scopes="scope1",
            provider_name="OIDCIDP_Minimal",
            provider_type="OIDC",
        )
        sso_provider = SSOIDPProviders(
            oidc=oidc_provider,
        )
        assert identity.upsert_identity_provider(self.pool_id, sso_provider)
        providers = identity.get_identity_providers(self.pool_id)
        assert providers.oidc
        assert providers.oidc.provider_name == "OIDCIDP_Minimal"
        assert providers.oidc.client_id == "test_id"

    def test_upsert_identity_provider_oidc_complete(self):
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
            provider_name="OIDCIDP_Complete",
            provider_type="OIDC",
        )
        sso_provider = SSOIDPProviders(
            oidc=oidc_provider,
        )
        assert identity.upsert_identity_provider(self.pool_id, sso_provider)
        providers = identity.get_identity_providers(self.pool_id)
        assert providers.oidc
        assert providers.oidc.provider_name == "OIDCIDP_Complete"
        assert providers.oidc.jwks_uri == "jwks://do.this"

    def test_delete_identity_provider(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            MetadataURL="http://somewhere.over.the.rainbow",
            provider_name="SamlIDP",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(saml=saml_provider)
        assert identity.upsert_identity_provider(self.pool_id, sso_provider)
        providers = identity.get_identity_providers(self.pool_id)
        assert providers.saml
        assert identity.delete_identity_provider(self.pool_id, saml_provider)
        providers = identity.get_identity_providers(self.pool_id)
        assert not providers.saml

    def test_get_identity_users(self):
        assert identity.get_identity_users(self.pool_id)[0].Username == self.username

    def test_create_identity_user_sparse(self):
        user = CognitoUser(UserPoolId=self.pool_id, Username="new_user")
        user_update = identity.create_identity_user(self.pool_id, user)
        assert len(identity.get_identity_users(self.pool_id)) == 2
        self.client.admin_delete_user(
            UserPoolId=self.pool_id, Username=user_update.Username
        )
        assert len(identity.get_identity_users(self.pool_id)) == 1

    def test_create_identity_user_complete(self):
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
        user_update = identity.create_identity_user(self.pool_id, user)
        assert len(identity.get_identity_users(self.pool_id)) == 2
        self.client.admin_delete_user(
            UserPoolId=self.pool_id, Username=user_update.Username
        )
        assert len(identity.get_identity_users(self.pool_id)) == 1

    def test_delete_identity_user(self):
        user = CognitoUser(UserPoolId=self.pool_id, Username="delete_user")
        _ = identity.create_identity_user(self.pool_id, user)
        assert len(identity.get_identity_users(self.pool_id)) == 2
        identity.delete_identity_user(self.pool_id, user)
        assert len(identity.get_identity_users(self.pool_id)) == 1

    def test_get_identity_groups(self):
        assert identity.get_identity_groups(self.pool_id)[0].GroupName == self.groupname

    def test_create_identity_group_sparse(self):
        group = CognitoGroup(UserPoolId=self.pool_id, GroupName="new_group")
        group_update = identity.create_identity_group(self.pool_id, group)
        assert len(identity.get_identity_groups(self.pool_id)) == 2
        self.client.delete_group(
            UserPoolId=self.pool_id, GroupName=group_update.GroupName
        )
        assert len(identity.get_identity_groups(self.pool_id)) == 1

    def test_create_identity_group_complete(self):
        group = CognitoGroup(
            UserPoolId=self.pool_id,
            GroupName="new_group",
            Description="a new group",
            RoleArn="aws:iam:::::",
        )
        group_update = identity.create_identity_group(self.pool_id, group)
        assert len(identity.get_identity_groups(self.pool_id)) == 2
        self.client.delete_group(
            UserPoolId=self.pool_id, GroupName=group_update.GroupName
        )
        assert len(identity.get_identity_groups(self.pool_id)) == 1

    def test_delete_identity_group(self):
        group = CognitoGroup(UserPoolId=self.pool_id, GroupName="delete_user")
        _ = identity.create_identity_group(self.pool_id, group)
        assert len(identity.get_identity_groups(self.pool_id)) == 2
        identity.delete_identity_group(self.pool_id, group)
        assert len(identity.get_identity_groups(self.pool_id)) == 1
