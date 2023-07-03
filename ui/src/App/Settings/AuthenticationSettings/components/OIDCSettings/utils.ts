export const parseOIDCFormData = settings => {
  const secrets = settings?.oidc?.secrets?.use
    ? {
        secrets: {
          oidc: {
            ...settings.secrets.oidc
          }
        }
      }
    : {};

  const get_user_by_oidc_settings = {
    get_user_by_oidc_settings: {
      metadata_url: settings.get_user_by_oidc_settings.metadata_url,
      client_scopes: settings.get_user_by_oidc_settings.client_scopes
        //remove empty strings
        .filter(x => !!x),
      include_admin_scope:
        settings.get_user_by_oidc_settings.include_admin_scope,
      grant_type: settings.get_user_by_oidc_settings.grant_type,
      id_token_response_key:
        settings.get_user_by_oidc_settings.id_token_response_key,
      access_token_response_key:
        settings.get_user_by_oidc_settings.access_token_response_key,
      jwt_email_key: settings.get_user_by_oidc_settings.jwt_email_key,
      enable_mfa: settings.get_user_by_oidc_settings.enable_mfa,
      get_groups_from_access_token:
        settings.get_user_by_oidc_settings.get_groups_from_access_token,
      access_token_audience:
        settings.get_user_by_oidc_settings.access_token_audience,
      get_groups_from_userinfo_endpoint:
        settings.get_user_by_oidc_settings.get_groups_from_userinfo_endpoint,
      user_info_groups_key:
        settings.get_user_by_oidc_settings.user_info_groups_key
    }
  };

  const auth = {
    auth: {
      get_user_by_oidc: true,
      get_user_by_saml: false,
      extra_auth_cookies: settings.auth.extra_auth_cookies,
      force_redirect_to_identity_provider:
        settings.auth.force_redirect_to_identity_provider
    }
  };

  return {
    ...get_user_by_oidc_settings,
    ...secrets,
    ...auth
  };
};
