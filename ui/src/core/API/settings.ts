import axios from '../Axios';
import { V4_API_URL } from './constants';

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

export const getAllUsers = query => {
  const url = `${V4_API_URL}/list_users`;
  return axios.post(url, query);
};

export const getAllGroups = query => {
  const url = `${V4_API_URL}/list_groups`;
  return axios.post(url, query);
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
