import axios from '../AxiosInstance';

export const getTenantUserpool = async () => {
  return axios.get('/api/v3/tenant/userpool');
};

export const setupAPIAuth = async session => {
  // Note on headers below - most browsers now implement Referrer Policy: strict-origin-when-cross-origin
  // and only specific headers are allowed: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy
  return axios.post(
    `/api/v1/auth/cognito`,
    { jwtToken: session },
    {
      // TODO: this will have to be un-hardcoded
      headers: {
        'Content-Type': 'application/json'
      }
    }
  );
};
