import axios from '../Axios';
import { V3_API_URL } from './constants';

export const getSlackInstallationStatus = async () => {
  const url = `${V3_API_URL}/slack`;
  const response = await axios.get(url);
  return response.data;
};

export const addNoqSlackApp = async () => {
  const url = `${V3_API_URL}/slack/install`;
  const response = await axios.get(url);
  return response.data;
};

export const deleteNoqSlackApp = async () => {
  const url = `${V3_API_URL}/slack`;
  const response = await axios.delete(url);
  return response.data;
};

export const getGithubInstallationStatus = async () => {
  const url = `${V3_API_URL}/github`;
  const response = await axios.get(url);
  return response.data;
};

export const addNoqGithubApp = async () => {
  const url = `${V3_API_URL}/github/install`;
  const response = await axios.get(url);
  return response.data;
};

export const deleteNoqGithubApp = async () => {
  const url = `${V3_API_URL}/github`;
  const response = await axios.delete(url);
  return response.data;
};

export const getGithubRepos = async () => {
  const url = `${V3_API_URL}/github/repos/`;
  const response = await axios.get(url);
  return response.data;
};
