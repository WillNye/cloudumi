import * as Yup from 'yup';

export const AUTH_DEFAULT_VALUES = {
  auth: {
    force_redirect_to_identity_provider: false,
    extra_auth_cookies: ['AWSELBAuthSessionCookie'],
    challenge_url: { enabled: false },
    logout_redirect_url: ''
  }
};

export enum AUTH_SETTINGS_TABS {
  SAML = 'SAML',
  OIDC = 'OIDC',
  SCIM = 'SCIM'
}
