import axios from '../Axios';
import { V1_API_URL, V2_API_URL, V4_API_URL } from './constants';

type RoleCredentialsParams = {
  requested_role: string;
};

type AWSRoleLoginParams = {
  roleQuery: string;
  search: string;
  extraArgs: string;
};

export const getEligibleRoles = query => {
  const url = `${V4_API_URL}/roles`;
  return axios.post(url, query);
};

export const getAllRoles = () => {
  const url = `${V2_API_URL}/policies?markdown=true&filters=%7B%22technology%22%3A%22AWS%3A%3AIAM%3A%3ARole%22%7D`;
  return axios.get(url);
};

export const getRoleCredentials = (data: RoleCredentialsParams) => {
  const url = `${V1_API_URL}/get_credentials`;
  return axios.post(url, data);
};

export const awsRoleLogin = ({
  roleQuery,
  search,
  extraArgs
}: AWSRoleLoginParams) => {
  const url = `${V2_API_URL}/role_login/${roleQuery}${search}${extraArgs}`;
  return axios.get(url);
};
