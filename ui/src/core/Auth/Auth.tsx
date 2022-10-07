import { FC, PropsWithChildren, useCallback, useMemo, useState } from 'react';
import { AuthProvider } from './AuthContext';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<any | null>(null);

  const login = useCallback(async () => {
    // TODO
  }, []);

  const logout = useCallback(async () => {
    // TODO
  }, []);

  const values = useMemo(
    () => ({
      user,
      login,
      logout
    }),
    [
      user,
      login,
      logout
    ]
  );

  return <AuthProvider value={values}>{children}</AuthProvider>;
};
