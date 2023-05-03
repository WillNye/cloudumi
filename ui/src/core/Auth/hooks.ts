import { Dispatch, useEffect } from 'react';
import axios from '../Axios';
import { User } from './types';

type AxiosInterceptorsProps = {
  setUser: Dispatch<User | null>;
  setInvalidTenant: Dispatch<boolean>;
  setInternalServerError: Dispatch<boolean>;
};

export const useAxiosInterceptors = ({
  setUser,
  setInvalidTenant,
  setInternalServerError
}: AxiosInterceptorsProps) => {
  useEffect(
    function onMount() {
      // Response Interceptor
      const interceptor = axios.interceptors.response.use(
        response => {
          return response;
        },

        error => {
          if (error?.response?.status === 401) {
            setUser(null);
          }

          if (error?.response?.status === 500) {
            setInternalServerError(true);
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
    },
    [setInvalidTenant, setUser, setInternalServerError]
  );
};
