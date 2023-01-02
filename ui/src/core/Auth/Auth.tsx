import {
  FC,
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState
} from 'react';
import { Auth as AmplifyAuth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';
import {
  AuthLoginInputs,
  AuthProvider,
  AuthResetPasswordInputs
} from './AuthContext';
import { ChallengeName } from './constants';
import { User } from './types';

import { useQuery, useMutation } from '@apollo/client';
import {
  AUTHENTICATE_NOQ_API_QUERY,
  GetTenantUserPoolQuery,
  GET_TENANT_USERPOOL_QUERY,
  GET_SSO_AUTH_REDIRECT_QUERY,
  WebResponse
} from 'core/graphql';
import '../AWS/Amplify';
import { getUserDetails } from 'core/API/auth';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [invalidTenant, setInvalidTenant] = useState(false);

  const navigate = useNavigate();

  useEffect(function onMount() {
    getUser();
  }, []);

  const getUser = useCallback(() => {
    setIsLoading(true);
    getUserDetails()
      .then(({ data }) => {
        setUser(data);
      })
      .catch(() => {
        navigate('/login');
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [navigate]);

  const values = useMemo(
    () => ({
      user,
      setUser,
      getUser
    }),
    [user, setUser, getUser]
  );

  // NOTE: I don't think we should put these 2 loading/invalid checks here
  if (isLoading) {
    // check is user data is available
    return <div>Loading...</div>;
  }

  if (invalidTenant) {
    // Invalid Tenant component
    return (
      <div>
        The Noq Platform for this tenant is currently unavailable. Please
        contact support.
      </div>
    );
  }

  return <AuthProvider value={values}>{children}</AuthProvider>;
};
