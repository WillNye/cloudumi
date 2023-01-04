import {
  FC,
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState
} from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { User } from './types';

import { getUserDetails } from 'core/API/auth';
import { Loader } from 'shared/elements/Loader';

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

  return <AuthProvider value={values}>{children}</AuthProvider>;
};
