import { FC, PropsWithChildren, useCallback, useMemo, useState } from 'react';
import { AuthLoginInputs, AuthProvider } from './AuthContext';
import { Auth as AmplifyAuth } from 'aws-amplify';
import '../AWS/Amplify';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<any | null>(null);

  const login = useCallback(async ({ username, password }: AuthLoginInputs) => {
    try {
      // NOTE: To get the token
      // const data = await Auth.currentSession()
      // return data.idToken.jwtToken

      const awsUser = await AmplifyAuth.signIn(username, password);
      setUser(awsUser);
    } catch (error) {
      console.error('error signing in', error);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await AmplifyAuth.signOut({ global: true });
    } catch (error) {
      console.log('error signing out: ', error);
    }
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
