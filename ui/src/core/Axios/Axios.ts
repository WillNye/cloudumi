import axios, { AxiosHeaders } from 'axios';
import { InternalAxiosRequestConfig } from 'axios';

const client = axios.create({
  baseURL: window.location.origin,
  // timeout: 10000,
  withCredentials: true,
  xsrfCookieName: '_xsrf',
  xsrfHeaderName: 'X-Xsrftoken'
});

// Request Interceptor
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const headers = new AxiosHeaders(config.headers);
    headers.set('Content-type', 'application/json;charset=UTF-8');
    headers.set('X-Requested-With', 'XMLHttpRequest');
    headers.set('Accept', 'application/json');

    const newConfig: InternalAxiosRequestConfig = {
      ...config,
      headers
    };
    return newConfig;
  },

  error => {
    // Error getting cookie
    return Promise.reject(error);
  }
);

export default client;
