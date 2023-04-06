import axios from '../Axios';
import { V3_API_URL } from './constants';

export const generateAWSLoginLink = (accountName: string) => {
  const url = `${V3_API_URL}/integrations/aws?account-name=${accountName}`;
  return axios.get(url);
};

export const getHubAccounts = () => {
  const url = `${V3_API_URL}/services/aws/account/hub`;
  return axios.get(url);
};

export const updateHubAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/hub`;
  return axios.post(url, data);
};

export const deleteHubAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  return axios.delete(url, { data });
};

export const getSpokeAccounts = () => {
  const url = `${V3_API_URL}/services/aws/account/spoke`;
  return axios.get(url);
};

export const deleteSpokeAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/spoke`;
  return axios.delete(url, { data });
};

export const updateSpokeAccount = data => {
  const url = `${V3_API_URL}/services/aws/account/spoke`;
  return axios.post(url, data);
};

export const getAWSOrganizations = () => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  return axios.get(url);
};

export const updateAWSOrganization = data => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  return axios.post(url, data);
};

export const deleteAWSOrganization = data => {
  const url = `${V3_API_URL}/services/aws/account/org`;
  return axios.delete(url, { data });
};

export const awsIntegrations = () => {
  const url = `${V3_API_URL}/integrations/aws`;
  return axios.get(url);
};
