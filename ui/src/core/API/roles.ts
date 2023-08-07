import cloneDeep from 'lodash/cloneDeep';
import axios from '../Axios';
import { V1_API_URL, V4_API_URL } from './constants';

const roleFilterToken = {
  propertyKey: 'iambic_template.template_type',
  operator: ':',
  value: 'NOQ::AWS::IAM::Role'
};

export const getEligibleRoles = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V4_API_URL}/roles`;
  const response = await axios.post(url, query);
  return response.data;
};

export const getAllRoles = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const newQuery = cloneDeep(query);
  newQuery.filtering.tokens.push(roleFilterToken);
  const url = `${V4_API_URL}/resources/datatable/`;
  const response = await axios.post(url, newQuery);
  return response.data;
};

export const getRoleCredentials = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V1_API_URL}/get_credentials`;
  const response = await axios.post(url, query);
  return response.data;
};
