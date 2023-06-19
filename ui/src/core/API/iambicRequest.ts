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
  const [_, provider, template_type] = queryKey;
  const url = `${V4_API_URL}/self-service/request-types`;
  const response = await axios.get(url, {
    params: {
      provider,
      template_type
    }
  });

  return response.data;
};

export const getRequestChangeDetails = async ({ queryKey }) => {
  const [_, requestTypeId, changeTypeId] = queryKey;
  const url = `${V4_API_URL}/self-service/request-types/${requestTypeId}/change-types/${changeTypeId}`;
  const response = await axios.get(url);
  return response.data;
};
