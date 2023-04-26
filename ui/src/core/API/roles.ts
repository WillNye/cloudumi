import axios from '../Axios';
import { V1_API_URL, V2_API_URL, V4_API_URL } from './constants';

export const getEligibleRoles = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V4_API_URL}/roles`;
  const response = await axios.post(url, query);
  return response.data;
};

export const getAllRoles = async () => {
  const url = `${V2_API_URL}/policies?markdown=true&filters=%7B%22technology%22%3A%22AWS%3A%3AIAM%3A%3ARole%22%7D`;
  const response = await axios.get(url);
  return response.data;
};

export const getRoleCredentials = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V1_API_URL}/get_credentials`;
  const response = await axios.post(url, query);
  return response.data;
};
