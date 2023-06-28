import * as Yup from 'yup';

export const AUTH_DEFAULT_VALUES = {
  auth: {
    force_redirect_to_identity_provider: false,
    extra_auth_cookies: ['AWSELBAuthSessionCookie'],
    challenge_url: { enabled: false },
    logout_redirect_url: ''
  }
};

export const DEFAULT_OIDC_SETTINGS = {
  oidc: {
    get_user_by_oidc_settings: {
      metadata_url: '',
      client_scopes: [],
      include_admin_scope: false,
      grant_type: 'authorization_code',
      id_token_response_key: 'id_token',
      access_token_response_key: 'access_token',
      jwt_email_key: 'email',
      enable_mfa: false,
      get_groups_from_access_token: true,
      access_token_audience: '',
      get_groups_from_userinfo_endpoint: true,
      user_info_groups_key: 'groups'
    },
    secrets: {
      use: false,
      oidc: {
        client_id: '',
        client_secret: ''
      }
    }
  }
};

export const DEFAULT_SAML_SETTINGS = {
  saml: {
    get_user_by_saml_settings: {
      jwt: {
        expiration_hours: 2,
        email_key: 'email',
        group_key: 'groups'
      },
      attributes: {
        user: 'user',
        groups: 'groups',
        email: 'email'
      },
      idp_metadata_url: '',
      sp: {
        entityId: '',
        assertionConsumerService: {
          binding: '',
          url: ''
        }
      },
      idp: {
        entityId: '',
        singleSignOnService: {
          binding: '',
          url: ''
        },
        singleLogoutService: {
          binding: '',
          url: ''
        },
        x509cert: ''
      }
    }
  }
};

// SAML Bindings: https://en.wikipedia.org/wiki/SAML_2.0#Bindings
export const BINDINGS = [
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
];

export const schema = Yup.object()
  .shape({
    ssoType: Yup.string()
      .oneOf(['none', 'oidc', 'saml'])
      .required('Required')
      .label('SSO Type'),
    auth: Yup.object()
      .shape({
        extra_auth_cookies: Yup.array()
          .of(Yup.string())
          .default([])
          .nullable()
          .label('Extra Auth Cookies'),
        force_redirect_to_identity_provider: Yup.boolean()
          .default(false)
          .label('Force Redirect to Identity Provider'),
        challenge_url: Yup.object().shape({
          enabled: Yup.boolean().default(true).label("Challenge URL's Enabled")
        }),
        logout_redirect_url: Yup.string()
          .url()
          .default('')
          .label('Logout Redirect URL')
      })
      .when('ssoType', {
        is: type => type != 'none',
        then: schema => schema.required(),
        otherwise: schema => schema.notRequired()
      }),
    oidc: Yup.object().when('ssoType', {
      is: 'oidc',
      then: schema =>
        schema
          .shape({
            get_user_by_oidc_settings: Yup.object().shape({
              metadata_url: Yup.string()
                .url()
                .default('')
                .label('Metadata URL'),
              client_scopes: Yup.array(
                Yup.string()
                  .ensure()
                  .min(1, x => `${x.label} must not be empty`)
                  .label('Client Scope')
              )
                .default([])
                .required()
                .label('Client Scopes'),
              include_admin_scope: Yup.boolean()
                .default(false)
                .label('Include Admin Scope'),
              grant_type: Yup.string()
                .default('authorization_code')
                .required()
                .label('Grant Type'),
              id_token_response_key: Yup.string()
                .default('id_token')
                .required()
                .label('ID Token Response Key'),
              access_token_response_key: Yup.string()
                .default('access_token')
                .required()
                .label('Access Token Response Key'),
              jwt_email_key: Yup.string()
                .default('email')
                .required()
                .label('JWT Email Key'),
              enable_mfa: Yup.boolean().default(false).label('Enable MFA'),
              get_groups_from_access_token: Yup.boolean()
                .default(false)
                .label('Get Groups from Access Token'),
              access_token_audience: Yup.string()
                .required()
                .label('Access Token Audience'),
              get_groups_from_userinfo_endpoint: Yup.boolean()
                .default(false)
                .label('Get Groups from User Info Endpoint'),
              user_info_groups_key: Yup.string()
                .default('groups')
                .required()
                .label("User Info's Groups Key")
            }),
            secrets: Yup.object().shape({
              use: Yup.boolean().default(false),
              oidc: Yup.object().when('use', {
                is: true,
                then: schema =>
                  schema.shape({
                    client_id: Yup.string()
                      .required()
                      .min(1)
                      .label('Client ID'),
                    client_secret: Yup.string()
                      .required()
                      .min(1)
                      .label('Client Secret')
                  })
              })
            })
          })
          .required(),
      otherwise: schema => schema.notRequired()
    }),
    saml: Yup.object().when('ssoType', {
      is: 'saml',
      then: schema =>
        schema
          .shape({
            get_user_by_saml_settings: Yup.object().shape({
              idp_metadata_url: Yup.string()
                .url()
                .default('')
                .label('IDP Metadata URL'),
              jwt: Yup.object().shape({
                expiration_hours: Yup.number()
                  .default(1)
                  .label('Expiration Hours'),
                email_key: Yup.string().default('email').label('Email Key'),
                group_key: Yup.string().default('groups').label('Group Key')
              }),
              attributes: Yup.object().shape({
                user: Yup.string().default('user').label('Attribute User'),
                groups: Yup.string()
                  .default('groups')
                  .label('Attribute Groups'),
                email: Yup.string().default('email').label('Attribute Email')
              }),
              idp: Yup.object().when('idp_metadata_url', {
                is: (idp_metadata_url: string) => !idp_metadata_url,
                then: schema =>
                  schema
                    .shape({
                      entityId: Yup.string().required().label('IDP Entity ID'),
                      singleSignOnService: Yup.object()
                        .shape({
                          binding: Yup.string()
                            .oneOf(BINDINGS)
                            .default(BINDINGS[0])
                            .required()
                            .label('IDP Single Sign On Service Binding'),
                          url: Yup.string()
                            .url()
                            .required()
                            .label('IDP Single Sign On Service URL')
                        })
                        .notRequired(),
                      singleLogoutService: Yup.object()
                        .shape({
                          binding: Yup.string()
                            .oneOf(BINDINGS)
                            .default(BINDINGS[0])
                            .required()
                            .label('IDP Single Logout Service Binding'),
                          url: Yup.string()
                            .url()
                            .required()
                            .label('IDP Single Logout Service URL')
                        })
                        .notRequired(),
                      x509cert: Yup.string().required().label('X509Cert')
                    })
                    .required(),
                otherwise: schema => schema.notRequired()
              }),
              sp: Yup.object()
                .shape({
                  assertionConsumerService: Yup.object().shape({
                    binding: Yup.string()
                      .oneOf([...BINDINGS, '', null])
                      .default('')
                      .notRequired()
                      .label('SP Assertion Consumer Service Binding'),
                    url: Yup.string().url().notRequired()
                  }),
                  entityId: Yup.string().label('SP Entity ID')
                })
                .notRequired()
            })
          })
          .required(),
      otherwise: schema => schema.notRequired()
    })
  })
  .required();
