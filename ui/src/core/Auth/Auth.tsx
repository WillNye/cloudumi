import { FC, PropsWithChildren, useMemo, useState } from 'react';
import { useMatch, useNavigate } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { User } from './types';

import { getUserDetails } from 'core/API/auth';
import { Loader } from 'shared/elements/Loader';
import { useAxiosInterceptors } from './hooks';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isUserLoggedIn } from './utils';
import { getGithubInstallationStatus } from 'core/API/integrations';
import { getHubAccounts } from 'core/API/awsConfig';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [invalidTenant, setInvalidTenant] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const isResetPasswordRoute = useMatch('/login/password-reset');

  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useAxiosInterceptors({ setUser, setInvalidTenant });

  const { refetch: getUser } = useQuery({
    queryKey: ['userProfile'],
    queryFn: getUserDetails,
    onSuccess: userData => {
      setUser(userData);
      queryClient.invalidateQueries({ queryKey: ['integrationsStatuses'] });
      queryClient.invalidateQueries({ queryKey: ['getHubAccounts'] });
      const preLoginPath = sessionStorage.getItem('preLoginPath');
      if (isUserLoggedIn(userData) && preLoginPath) {
        sessionStorage.removeItem('preLoginPath');
        window.location.href = preLoginPath;
      }
      setIsLoading(false);
    },
    onError: () => {
      const relativePath = window.location.pathname + window.location.search;
      if (!relativePath?.startsWith('/login')) {
        sessionStorage.setItem('preLoginPath', relativePath);
      }
      if (!isResetPasswordRoute) {
        navigate('/login');
      }
      setIsLoading(false);
    }
  });

  const { data: githubData } = useQuery({
    queryFn: getGithubInstallationStatus,
    queryKey: ['githubIntegrationStatus']
  });

  const { data: hubAccount } = useQuery({
    queryFn: getHubAccounts,
    queryKey: ['getHubAccounts']
  });

  const isHubAccountInstalled = useMemo(
    () => Boolean(hubAccount?.count),
    [hubAccount?.count]
  );
  const isGithubInstalled = useMemo(
    () => Boolean(githubData?.data?.installed),
    [githubData?.data]
  );

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

  return (
    <AuthProvider
      value={{
        isHubAccountInstalled,
        isGithubInstalled,
        user,
        setUser,
        getUser
      }}
    >
      {children}
    </AuthProvider>
  );
};
