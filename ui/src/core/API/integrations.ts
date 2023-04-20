import axios from '../Axios';
import { V3_API_URL } from './constants';

export const getSlackInstallationStatus = () => {
  const url = `${V3_API_URL}/slack`;
  return axios.get(url);
};

export const addNoqSlackApp = () => {
  const url = `${V3_API_URL}/slack/install`;
  return axios.get(url);
};

export const deleteNoqSlackApp = () => {
  const url = `${V3_API_URL}/slack`;
  return axios.delete(url);
};
