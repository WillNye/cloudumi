import axios from '../Axios';
import { V4_API_URL } from './constants';

export const getProviders = async () => {
  const url = `${V4_API_URL}/providers`;
  const response = await axios.get(url);
  return response.data;
};

export const getChangeRequestType = async ({ queryKey }) => {
  const [_, id] = queryKey;
  const url = `${V4_API_URL}/self-service/request-types/${id}/change-types/`;
  const response = await axios.get(url);
  return response.data;
};

export const getRequestType = async ({ queryKey }) => {
  const [_, id] = queryKey;
  const url = `${V4_API_URL}/self-service/request-types?provider=${id}`;
  const response = await axios.get(url);
  return response.data;
};
