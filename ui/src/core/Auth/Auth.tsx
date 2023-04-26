import { FC, PropsWithChildren, useMemo, useState } from 'react';
import { useMatch, useNavigate } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { User } from './types';

import { getUserDetails } from 'core/API/auth';
import { Loader } from 'shared/elements/Loader';
import { useAxiosInterceptors } from './hooks';
import { useQuery } from '@tanstack/react-query';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [invalidTenant, setInvalidTenant] = useState(false);
  const [internalServerError, setInternalServerError] = useState(false);

  const isResetPasswordRoute = useMatch('/login/password-reset');

  const navigate = useNavigate();

  useAxiosInterceptors({ setUser, setInvalidTenant, setInternalServerError });

  const { isLoading, refetch: getUser } = useQuery({
    queryKey: ['userProfile'],
    queryFn: getUserDetails,
    onSuccess: userData => {
      setUser(userData);
    },
    onError: () => {
      if (!isResetPasswordRoute) {
        navigate('/login');
      }
    }
  });

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
    return <Loader fullPage />;
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

  if (internalServerError) {
    // Invalid Tenant component
    return <div>Internal server error</div>;
  }

  return <AuthProvider value={values}>{children}</AuthProvider>;
};
