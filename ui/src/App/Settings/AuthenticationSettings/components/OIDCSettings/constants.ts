import * as Yup from 'yup';

export const oidcSchema = Yup.object()
  .shape({
    get_user_by_oidc_settings: Yup.object().shape({
      metadata_url: Yup.string().url().default('').label('Metadata URL'),
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
      oidc: Yup.object().shape({
        client_id: Yup.string().label('Client ID'),
        client_secret: Yup.string()
          .label('Client Secret')
          .when('client_id', {
            is: v => v != '',
            then: schema => schema.required().min(1)
          })
      })
    })
  })
  .required();

export const DEFAULT_OIDC_SETTINGS = {
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
    access_token_audience: 'noq',
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
};
