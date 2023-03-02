import axios from 'axios';

export const getCookie = name => {
  const r = document.cookie.match('\\b' + name + '=([^;]*)\\b');
  return r ? r[1] : undefined;
};

const client = axios.create({
  baseURL: window.location.origin,
  // timeout: 10000,
  withCredentials: true
});

// Request Interceptor
client.interceptors.request.use(
  config => {
    const newConfig = {
      ...config,
      Headers: {
        ...config.headers,
        'Content-type': 'application/json',
        'X-Xsrftoken': getCookie('_xsrf'),
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json'
      }
    };
    return newConfig;
  },

  error => {
    // Error getting cookie
    return Promise.reject(error);
  }
);

export default client;
