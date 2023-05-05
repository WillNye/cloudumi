import axios from '../Axios';
import { V4_API_URL } from './constants';

export const getAllResources = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V4_API_URL}/resources/datatable`;
  const response = await axios.post(url, query);
  return response.data;
};

export const getResource = async ({ queryKey }) => {
  const [_, id] = queryKey;
  const url = `${V4_API_URL}/resources/${id}`;
  const response = await axios.get(url);
  return response.data;
};
