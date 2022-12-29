import axios from '../Axios';
import { V4_API_URL } from './constants';

type LoginParams = {
  username: string;
  password: string;
};

export const login = (data: LoginParams) => {
  const url = `${V4_API_URL}/login/`;
  return axios.post(url, data);
};

// Not yet implemented in the backend
export const logout = () => {
  const url = `${V4_API_URL}/logout/`;
  return axios.post(url);
};

export const setupMFA = () => {
  const url = `${V4_API_URL}/users/mfa/`;
  return axios.post(url);
};

export const verifyMFA = () => {
  const url = `${V4_API_URL}/users/mfa/`;
  return axios.post(url);
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
  const url = `${V4_API_URL}/api/v1/auth?sso_signin=true/`;
  return axios.post(url);
};
