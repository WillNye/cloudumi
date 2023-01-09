import { useEffect } from 'react';
import axios from '../Axios';

export const useAxiosInterceptors = ({ setUser, setInvalidTenant }) => {
  useEffect(function onMount() {
    // Response Interceptor
    const interceptor = axios.interceptors.response.use(
      response => {
        return response;
      },

      error => {
        if (error?.response?.status === 401) {
          //   setUser(null);
        }

        if (error?.response?.status === 500) {
          // log sentry error
        }

        if (error?.response?.status === 406) {
          setInvalidTenant(true);
        }

        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(interceptor);
    };
  }, []);
};
