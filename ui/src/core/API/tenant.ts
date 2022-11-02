import axios from '../AxiosInstance';

export const getTenantUserpool = async () => {
  return axios.get('/api/v3/tenant/userpool');
};
