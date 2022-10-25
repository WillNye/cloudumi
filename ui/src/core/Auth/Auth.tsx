import { FC, PropsWithChildren, useCallback, useMemo, useState } from 'react';
import { AuthLoginInputs, AuthProvider } from './AuthContext';
import { Auth as AmplifyAuth } from 'aws-amplify';
import '../AWS/Amplify';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<any | null>(null);

  const login = useCallback(async ({ username, password }: AuthLoginInputs) => {
    try {
      // References: https://docs.amplify.aws/lib/auth/manageusers/q/platform/js/
      const awsUser = await AmplifyAuth.signIn(username, password);

      // NOTE: For making API requests later, we will need the token
      // here is how you get that ->
      // const { idToken: { jwtToken } } = await Auth.currentSession();
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
