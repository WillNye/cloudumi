import { Dispatch, useEffect } from 'react';
import axios from '../Axios';
import { User } from './types';

type AxiosInterceptorsProps = {
  setUser: Dispatch<User | null>;
  setInvalidTenant: Dispatch<boolean>;
};

export const useAxiosInterceptors = ({
  setUser,
  setInvalidTenant
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
    [setInvalidTenant, setUser]
  );
};
