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

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [invalidTenant, setInvalidTenant] = useState(false);

  const values = useMemo(
    () => ({
      user,
      setUser
    }),
    [user, setUser]
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
