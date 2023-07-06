import axios from '../Axios';
import { V4_API_URL } from './constants';

export const getProviders = async () => {
  const url = `${V4_API_URL}/providers`;
  const response = await axios.get(url);
  return response.data;
};

export const getProviderDefinitions = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V4_API_URL}/providers/definitions?provider=${query.provider}&iambic_template_id=${query.template_id}`;
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

export const getRequestTemplateTypes = async ({ queryKey }) => {
  const [_, provider] = queryKey;
  const url = `${V4_API_URL}/template-types?provider=${provider}`;
  const response = await axios.get(url);
  return response.data;
};

export const getRequestChangeDetails = async ({ queryKey }) => {
  const [_, requestTypeId, changeTypeId] = queryKey;
  const url = `${V4_API_URL}/self-service/request-types/${requestTypeId}/change-types/${changeTypeId}`;
  const response = await axios.get(url);
  return response.data;
};

export const getAllRequests = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V4_API_URL}/self-service/requests/datatable`;
  const response = await axios.post(url, query);
  return response.data;
};

export const getIambicRequest = async ({ queryKey }) => {
  const [_, requestId] = queryKey;
  const url = `${V4_API_URL}/self-service/requests/${requestId}`;
  const response = await axios.get(url);
  return response.data;
};

export const createIambicRequest = async data => {
  const url = `${V4_API_URL}/self-service/requests/`;
  const response = await axios.post(url, data);
  return response.data;
};
