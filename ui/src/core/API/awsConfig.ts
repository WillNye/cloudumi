import axios from '../Axios';
import { V3_API_URL } from './constants';

export const generateAWSLoginLink = (accountName: string) => {
  const url = `${V3_API_URL}/integrations/aws?account-name=${accountName}`;
  return axios.get(url);
};

export const getHubAccount = () => {
  const url = `${V3_API_URL}/services/aws/account/hub`;
  return axios.get(url);
};

export const getSpokeAccount = () => {
  const url = `${V3_API_URL}/services/aws/account/spoke`;
  return axios.get(url);
};
