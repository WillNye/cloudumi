from unittest import TestCase

import boto3
import moto

from common.lib.cognito import identity
from common.models import (
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
        client = boto3.client("cognito-idp")
        self.pool_name = "test_pool"
        self.pool_response = client.create_user_pool(PoolName=self.pool_name)
        self.pool_id = self.pool_response.get("UserPool", {}).get("Id")
        client.create_identity_provider(
            UserPoolId=self.pool_id,
            ProviderName="test_provider",
            ProviderType="SAML",
            ProviderDetails={
                "MetadataURL": "http://somewhere.yo.dawgs",
            },
        )

    def test_get_identity(self):
        providers = identity.get_identity_providers(self.pool_id)
        assert providers[0].get("ProviderName") == "test_provider"

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
        assert len([x for x in providers if x.get("ProviderName") == "GoogleIDP"]) == 1

    def test_upsert_identity_provider_saml(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            metadata_url="http://somewhere.over.the.rainbow",
            provider_name="SamlIDP",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(
            saml=saml_provider,
        )
        assert identity.upsert_identity_provider(self.pool_id, sso_provider)
        providers = identity.get_identity_providers(self.pool_id)
        assert len([x for x in providers if x.get("ProviderName") == "SamlIDP"]) == 1

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
        assert (
            len([x for x in providers if x.get("ProviderName") == "OIDCIDP_Minimal"])
            == 1
        )

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
        assert (
            len([x for x in providers if x.get("ProviderName") == "OIDCIDP_Complete"])
            == 1
        )

    def test_delete_identity_provider(self):
        saml_provider = SamlOIDCSSOIDPProvider(
            metadata_url="http://somewhere.over.the.rainbow",
            provider_name="SamlIDP",
            provider_type="SAML",
        )
        sso_provider = SSOIDPProviders(saml=saml_provider)
        assert identity.upsert_identity_provider(self.pool_id, sso_provider)
        assert len(identity.get_identity_providers(self.pool_id)) == 2
        assert identity.delete_identity_provider(self.pool_id, saml_provider)
        assert len(identity.get_identity_providers(self.pool_id)) == 1
