import axios from 'axios';

const client = axios.create({
  // not sure if its the best way to get the host url
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

    return Promise.reject(error);
  }
);

export default client;
