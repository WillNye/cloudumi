import axios from 'axios';

const client = axios.create({
  baseURL: window.location.origin,
  timeout: 10000,
  withCredentials: true
});

// Request Interceptor
client.interceptors.request.use(
  config => {
    // add cookie to request
    return config;
  },

  error => {
    // Error getting cookie
    return Promise.reject(error);
  }
);

// Response Interceptor
client.interceptors.response.use(
  response => {
    return response;
  },

  error => {
    if (error.response.status === 401) {
      // logout user
    }

    if (error.response.status === 500) {
      // log sentry error
    }

    if (error.response.status === 406) {
      // show invalid client page
    }

    return Promise.reject(error);
  }
);

export default client;
