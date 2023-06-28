import { FC, PropsWithChildren, useMemo, useState } from 'react';
import { useMatch, useNavigate } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { User } from './types';

import { getUserDetails } from 'core/API/auth';
import { Loader } from 'shared/elements/Loader';
import { useAxiosInterceptors } from './hooks';
import { useQuery } from '@tanstack/react-query';
import { ErrorFallback } from 'shared/elements/ErrorFallback';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [invalidTenant, setInvalidTenant] = useState(false);
  const [internalServerError, setInternalServerError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const isResetPasswordRoute = useMatch('/login/password-reset');

  const navigate = useNavigate();

  useAxiosInterceptors({ setUser, setInvalidTenant, setInternalServerError });

  const { refetch: getUser } = useQuery({
    queryKey: ['userProfile'],
    queryFn: getUserDetails,
    onSuccess: userData => {
      setUser(userData);
      setIsLoading(false);
    },
    onError: () => {
      const relativePath = window.location.pathname + window.location.search;
      sessionStorage.setItem('preLoginPath', relativePath);
      if (!isResetPasswordRoute) {
        navigate('/login');
      }
      setIsLoading(false);
    }
  });

  const preLoginPath = sessionStorage.getItem('preLoginPath');
  if (user && preLoginPath) {
    sessionStorage.removeItem('preLoginPath');
    window.location.href = preLoginPath;
  }

  const values = useMemo(
    () => ({
      user,
      setUser,
      getUser,
      setInternalServerError
    }),
    [user, setUser, getUser, setInternalServerError]
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

  // if (internalServerError) {
  //   // Handle Internal Server Error
  //   return <ErrorFallback fullPage />;
  // }

  return <AuthProvider value={values}>{children}</AuthProvider>;
};
