import axios from '../Axios';
import { V4_API_URL } from './constants';
import { IWebResponse } from './types';

const SAML_URL = `${V4_API_URL}/auth/sso/saml`;
const OIDC_URL = `${V4_API_URL}/auth/sso/oidc`;

export const fetchOidcWellKnownConfig = async (url): Promise<any> => {
  const { data } = await axios.get(url);
  return data;
};

export const fetchOidcSettings = async (): Promise<
  IWebResponse<OIDCResponse>
> => {
  const { data } = await axios.get(OIDC_URL);
  return data;
};

export const fetchSamlSettings = async (): Promise<
  IWebResponse<SAMLResponse>
> => {
  const { data } = await axios.get(SAML_URL);
  return data;
};

export const updateSAMLSettings = async (
  data: any
): Promise<IWebResponse<any>> => {
  return axios.post(SAML_URL, data);
};

export const updateOIDCSettings = async (
  data: any
): Promise<IWebResponse<any>> => {
  return axios.post(OIDC_URL, data);
};

export const deleteSamlSettings = async (): Promise<IWebResponse<void>> => {
  return axios.delete(SAML_URL);
};

export const deleteOidcSettings = async (): Promise<IWebResponse<void>> => {
  return axios.delete(OIDC_URL);
};

// Response Types
// TODO: move these to a shared or special location
export interface OIDCResponse {
  get_user_by_oidc_settings: GetUserByOidcSettings;
  auth: Auth;
  secrets?: {
    oidc: {
      client_id: string;
      client_secret: string;
    };
  };
}

export interface GetUserByOidcSettings {
  metadata_url: string;
  client_scopes?: string[] | null;
  include_admin_scope: boolean;
  grant_type: string;
  id_token_response_key: string;
  access_token_response_key: string;
  jwt_email_key: string;
  enable_mfa: boolean;
  get_groups_from_access_token: boolean;
  access_token_audience: string;
  get_groups_from_userinfo_endpoint: boolean;
  user_info_groups_key: string;
}

export interface Auth {
  get_user_by_oidc: boolean;
  get_user_by_saml: boolean;
  extra_auth_cookies?: string[] | null;
  force_redirect_to_identity_provider: boolean;
  challenge_url?: { enabled: boolean };
  logout_redirect_url?: string;
}

export interface SAMLResponse {
  get_user_by_saml_settings: GetUserBySamlSettings;
  auth: Auth;
}
export interface GetUserBySamlSettings {
  jwt: Jwt;
  attributes: Attributes;
  idp: Idp;
  sp: ServiceProvider;
  idp_metadata_url?: string;
}

export interface Jwt {
  expiration_hours: number;
  email_key: string;
  group_key: string;
}

export interface Attributes {
  user: string;
  groups: string;
  email: string;
}

export interface Idp {
  entityId: string;
  singleSignOnService: BindingService;
  singleLogoutService: BindingService;
  x509cert: string;
}

export interface BindingService {
  binding: string;
  url: string;
}

export interface ServiceProvider {
  assertionConsumerService: BindingService;
  entityId: string;
}
