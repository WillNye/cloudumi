import axios from 'axios';

const client = axios.create({
  baseURL: window.location.origin,
  // timeout: 10000,
  withCredentials: true,
  xsrfCookieName: '_xsrf',
  xsrfHeaderName: 'X-Xsrftoken'
});

// Request Interceptor
client.interceptors.request.use(
  config => {
    const newConfig = {
      ...config,
      headers: {
        ...config.headers,
        'Content-type': 'application/json',
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
