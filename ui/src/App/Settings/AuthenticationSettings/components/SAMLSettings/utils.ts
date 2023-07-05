export const parseSAMLFormData = settings => {
  const get_user_by_saml_settings = {
    get_user_by_saml_settings: {
      jwt: {
        expiration_hours: 2
      },
      attributes: {
        user: settings.attributes.user,
        groups: settings.attributes.groups,
        email: settings.attributes.email
      },
      idp_metadata_url: settings.use_metadata_url
        ? settings.idp_metadata_url
        : null,
      // if idp_metadata_url is not set, use idp object
      ...(!settings.use_metadata_url
        ? {
            idp: {
              entityId: settings.idp.entityId,
              singleSignOnService: {
                binding: settings.idp.singleSignOnService.binding,
                url: settings.idp.singleSignOnService.url
              },
              singleLogoutService: {
                binding: settings.idp.singleLogoutService.binding,
                url: settings.idp.singleLogoutService.url
              },
              x509cert: settings.idp.x509cert
            }
          }
        : { idp: null }),
      // if sp is not set, then set it to null
      sp: {
        // if entityId is not set, then set it to null
        ...(settings.sp.entityId && {
          entityId: settings.sp.entityId
        }),
        // if assertionConsumerService is not set, then set it to null
        ...(settings?.sp?.assertionConsumerService?.url
          ? {
              assertionConsumerService: {
                binding: settings.sp.assertionConsumerService.binding,
                url: settings.sp.assertionConsumerService.url
              }
            }
          : null)
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
};
