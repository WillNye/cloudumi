import axios from '../Axios';
import { V2_API_URL } from './constants';

export const getEligibleRoles = () => {
  const url = `${V2_API_URL}/eligible_roles`;
  return axios.get(url);
};

export const getAllRoles = () => {
  const url = `${V2_API_URL}/policies?markdown=true&filters=%7B%22technology%22%3A%22AWS%3A%3AIAM%3A%3ARole%22%7D`;
  return axios.get(url);
};
