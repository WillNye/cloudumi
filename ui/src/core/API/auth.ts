import axios from '../Axios';
import { V2_API_URL, V4_API_URL } from './constants';

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

export const getUserDetails = () => {
  const url = `${V2_API_URL}/user_profile`;
  return axios.get(url);
};

export const completePassword = (data: CompletePasswordParams) => {
  const url = `${V4_API_URL}/users/password_reset`;
  return axios.post(url, data);
};

export const resetPassword = () => {
  const url = `${V4_API_URL}/users/forgot_password`;
  return axios.post(url);
};

// Not yet implemented in the backend
export const signup = () => {
  const url = `${V4_API_URL}/users/signup`;
  return axios.post(url);
};

export const signinWithSSO = () => {
  const url = `${V4_API_URL}/api/v1/auth?sso_signin=true`;
  return axios.post(url);
};
