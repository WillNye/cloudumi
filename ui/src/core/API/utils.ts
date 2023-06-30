export const extractErrorMessage = error => {
  if (typeof error === 'string') {
    return error;
  } else if (error && typeof error === 'object') {
    if (error.message) {
      return error.message;
    } else if (error.error) {
      return error.error;
    } else if (Array.isArray(error)) {
      return error.map(e => extractErrorMessage(e)).join(', ');
    } else if (error.data) {
      return extractErrorMessage(error.data);
    } else if (error.errors) {
      return extractErrorMessage(error.errors);
    }
  }
  return '';
};

/**
 * Parse body to save settings
 * @param settings
 * @returns
 */
export const parseSsoSettingsBody = (settings, ssoType) => {
  if (ssoType == 'oidc') {
    const secrets = settings?.oidc?.secrets?.use
      ? {
          secrets: {
            oidc: {
              ...settings.oidc.secrets.oidc
            }
          }
        }
      : {};

    const get_user_by_oidc_settings = {
      get_user_by_oidc_settings: {
        metadata_url: settings.oidc.get_user_by_oidc_settings.metadata_url,
        client_scopes: settings.oidc.get_user_by_oidc_settings.client_scopes
          //remove empty strings
          .filter(x => !!x),
        include_admin_scope:
          settings.oidc.get_user_by_oidc_settings.include_admin_scope,
        grant_type: settings.oidc.get_user_by_oidc_settings.grant_type,
        id_token_response_key:
          settings.oidc.get_user_by_oidc_settings.id_token_response_key,
        access_token_response_key:
          settings.oidc.get_user_by_oidc_settings.access_token_response_key,
        jwt_email_key: settings.oidc.get_user_by_oidc_settings.jwt_email_key,
        enable_mfa: settings.oidc.get_user_by_oidc_settings.enable_mfa,
        get_groups_from_access_token:
          settings.oidc.get_user_by_oidc_settings.get_groups_from_access_token,
        access_token_audience:
          settings.oidc.get_user_by_oidc_settings.access_token_audience,
        get_groups_from_userinfo_endpoint:
          settings.oidc.get_user_by_oidc_settings
            .get_groups_from_userinfo_endpoint,
        user_info_groups_key:
          settings.oidc.get_user_by_oidc_settings.user_info_groups_key
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
  } else if (ssoType == 'saml') {
    const get_user_by_saml_settings = {
      get_user_by_saml_settings: {
        jwt: {
          expiration_hours: 2
        },
        attributes: {
          user: settings.saml.get_user_by_saml_settings.attributes.user,
          groups: settings.saml.get_user_by_saml_settings.attributes.groups,
          email: settings.saml.get_user_by_saml_settings.attributes.email
        },
        idp_metadata_url:
          settings.saml.get_user_by_saml_settings.idp_metadata_url ?? null,
        // if idp_metadata_url is not set, use idp object
        ...(!settings.saml.get_user_by_saml_settings.idp_metadata_url
          ? {
              idp: {
                entityId: settings.saml.get_user_by_saml_settings.idp.entityId,
                singleSignOnService: {
                  binding:
                    settings.saml.get_user_by_saml_settings.idp
                      .singleSignOnService.binding,
                  url: settings.saml.get_user_by_saml_settings.idp
                    .singleSignOnService.url
                },
                singleLogoutService: {
                  binding:
                    settings.saml.get_user_by_saml_settings.idp
                      .singleLogoutService.binding,
                  url: settings.saml.get_user_by_saml_settings.idp
                    .singleLogoutService.url
                },
                x509cert: settings.saml.get_user_by_saml_settings.idp.x509cert
              }
            }
          : { idp: null }),
        // if sp is not set, then set it to null
        sp: {
          // if entityId is not set, then set it to null
          ...(settings.saml.get_user_by_saml_settings.sp.entityId && {
            entityId: settings.saml.get_user_by_saml_settings.sp.entityId
          }),
          // if assertionConsumerService is not set, then set it to null
          ...(settings.saml.get_user_by_saml_settings.sp
            .assertionConsumerService
            ? {
                assertionConsumerService: {
                  binding:
                    settings.saml.get_user_by_saml_settings.sp
                      .assertionConsumerService.binding,
                  url: settings.saml.get_user_by_saml_settings.sp
                    .assertionConsumerService.url
                }
              }
            : { sp: null })
        }
      }
    };

    const auth = {
      auth: {
        get_user_by_oidc: false,
        get_user_by_saml: true,
        extra_auth_cookies: settings.auth.extra_auth_cookies,
        force_redirect_to_identity_provider:
          settings.auth.force_redirect_to_identity_provider
      }
    };

    return {
      ...get_user_by_saml_settings,
      ...auth
    };
  } else {
    return null;
  }
};
