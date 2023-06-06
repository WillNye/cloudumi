import axios from '../Axios';
import { V4_API_URL } from './constants';

export const getProviders = async () => {
  const url = `${V4_API_URL}/providers`;
  const response = await axios.get(url);
  return response.data;
};
