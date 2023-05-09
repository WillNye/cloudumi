import axios from '../Axios';
import { V1_API_URL, V2_API_URL, V3_API_URL, V4_API_URL } from './constants';

type LoginParams = {
  email: string;
  password: string;
};

type CompletePasswordParams = {
  new_password: string;
  current_password: string;
};

type SetupMFAParams = {
  command: 'setup' | 'verify';
  mfa_token?: string;
};

type VerifyMFAParams = {
  mfa_token: string;
};

type ForgotPasswordParams = {
  command: 'request' | 'reset';
  email?: string;
  password?: string;
  token?: string;
};

export const login = (data: LoginParams) => {
  const url = `${V4_API_URL}/users/login`;
  return axios.post(url, data);
};

// Not yet implemented in the backend
export const logout = () => {
  const url = `${V2_API_URL}/logout`;
  return axios.post(url);
};

export const setupMFA = (data: SetupMFAParams) => {
  const url = `${V4_API_URL}/users/mfa`;
  return axios.post(url, data);
};

export const verifyMFA = (data: VerifyMFAParams) => {
  const url = `${V4_API_URL}/users/login/mfa/`;
  return axios.post(url, data);
};

export const getUserDetails = async () => {
  const url = `${V2_API_URL}/user_profile`;
  const response = await axios.get(url);
  return response.data;
};

export const completePassword = (data: CompletePasswordParams) => {
  const url = `${V4_API_URL}/users/password_reset`;
  return axios.post(url, data);
};

export const resetPassword = (data: ForgotPasswordParams) => {
  const url = `${V4_API_URL}/users/forgot_password`;
  return axios.post(url, data);
};

export const signinWithSSO = () => {
  const url = `${V1_API_URL}/auth?sso_signin=true`;
  return axios.get(url);
};

export const awsSignIn = async ({ queryKey }) => {
  const [_, role] = queryKey;
  const url = `${V2_API_URL}/role_login/${role}`;
  const response = await axios.get(url);
  return response.data;
};

export const getEndUserAgreement = () => {
  const url = `${V3_API_URL}/legal/agreements/eula`;
  return axios.get(url);
};

export const acceptEndUserAgreement = () => {
  const url = `${V3_API_URL}/tenant/details/eula`;
  return axios.post(url);
};

export const checkPasswordComplexity = async data => {
  const url = `${V4_API_URL}/users/password/complexity`;
  const response = await axios.post(url, data);
  return response.data;
};
