import axios from '../Axios';
import { V3_API_URL } from './constants';

export const generateAWSLoginLink = async ({ queryKey }) => {
  const [_, accountName] = queryKey;
  const url = `${V3_API_URL}/integrations/aws?account-name=${accountName}`;
  const response = await axios.get(url);
  return response.data;
};

export const getHubAccounts = async () => {
  const url = `${V3_API_URL}/services/aws/account/hub`;
  const response = await axios.get(url);
  return response.data;
};

export const updateHubAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/hub`;
  return axios.post(url, data);
};

export const deleteHubAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  return axios.delete(url, { data });
};

export const getSpokeAccounts = async () => {
  const url = `${V3_API_URL}/services/aws/account/spoke`;
  const response = await axios.get(url);
  return response.data;
};

export const deleteSpokeAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/spoke`;
  return axios.delete(url, { data });
};

export const updateSpokeAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/spoke`;
  return axios.post(url, data);
};

export const getAWSOrganizations = async () => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  const response = await axios.get(url);
  return response.data;
};

export const updateAWSOrganization = data => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  return axios.post(url, data);
};

export const deleteAWSOrganization = data => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  return axios.delete(url, { data });
};

export const awsIntegrations = async () => {
  const url = `${V3_API_URL}/integrations/aws`;
  const response = await axios.get(url);
  return response.data;
};
