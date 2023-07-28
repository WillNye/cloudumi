import axios from '../Axios';
import { V4_API_URL } from './constants';
import { IWebResponse } from './types';

export const createUser = data => {
  const url = `${V4_API_URL}/users`;
  return axios.post(url, data);
};

export const deleteUser = data => {
  const url = `${V4_API_URL}/users`;
  return axios.delete(url, { data });
};

export const updateUser = (data, action) => {
  const url = `${V4_API_URL}/users?user_id=${data.id}&action=${action}`;
  return axios.put(url, data);
};

export const getAllUsers = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V4_API_URL}/list_users`;
  const response = await axios.post(url, query);
  return response.data;
};

export const getAllGroups = async ({ queryKey }) => {
  const [_, query] = queryKey;
  const url = `${V4_API_URL}/list_groups`;
  const response = await axios.post(url, query);
  return response.data;
};

export const createGroup = data => {
  const url = `${V4_API_URL}/groups`;
  return axios.post(url, data);
};

export const updateGroup = data => {
  const url = `${V4_API_URL}/groups`;
  return axios.put(url, data);
};

export const deleteGroup = data => {
  const url = `${V4_API_URL}/groups`;
  return axios.delete(url, { data });
};

export const createGroupMemberships = data => {
  const url = `${V4_API_URL}/group_memberships`;
  return axios.post(url, data);
};

export const deleteGroupMemberships = data => {
  const url = `${V4_API_URL}/group_memberships`;
  return axios.delete(url, { data });
};

export const getAdminGroups = async () => {
  const url = `${V4_API_URL}/groups_can_admin`;
  const response = await axios.get<{ data: string[] }>(url);
  return response.data;
};

export const addAdminGroups = async (data: { groups: string[] }) => {
  const url = `${V4_API_URL}/groups_can_admin`;
  const response = await axios.put<PartialWebResponse>(url, data);
  return response;
};

export const deleteAdminGroups = async (data: { groups: string[] }) => {
  const url = `${V4_API_URL}/groups_can_admin`;
  const response = await axios.delete<PartialWebResponse>(url, { data });
  return response;
};

export type PartialWebResponse = Pick<
  IWebResponse<any>,
  'data' | 'status' | 'status_code'
>;
