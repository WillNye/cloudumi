import { FC, PropsWithChildren, useCallback, useMemo, useState } from 'react';
import { AuthLoginInputs, AuthProvider, AuthResetPasswordInputs } from './AuthContext';
import { Auth as AmplifyAuth } from 'aws-amplify';
import '../AWS/Amplify';
import { useNavigate } from 'react-router-dom';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<any | null>(null);
  const navigate = useNavigate();

  const changePassword = useCallback(async ({ oldPassword, newPassword }: AuthResetPasswordInputs) => {
    try {
      // Note: Not sure if we want to do this
      // const user = await AmplifyAuth.currentAuthenticatedUser()
      await AmplifyAuth.changePassword(user, oldPassword, newPassword);

      // After login, we should redirect to the main page
      navigate('/');
    } catch ({ message }) {
      throw new Error(`Error changing password: ${message}`);
    }
  }, [user, navigate]);

  const login = useCallback(async ({ username, password }: AuthLoginInputs) => {
    try {
      // References: https://docs.amplify.aws/lib/auth/manageusers/q/platform/js/
      const awsUser = await AmplifyAuth.signIn(username, password);

      // NOTE: For making API requests later, we will need the token
      // here is how you get that ->
      // const { idToken: { jwtToken } } = await Auth.currentSession();
      setUser(awsUser);

      navigate('/');
    } catch ({ message }) {
      throw new Error(`Error logging in: ${message}`);
    }
  }, [navigate]);

  const logout = useCallback(async () => {
    try {
      await AmplifyAuth.signOut({ global: true });
    } catch ({ message }) {
      throw new Error(`Error logging out: ${message}`);
    }
  }, []);

  const values = useMemo(
    () => ({
      user,
      login,
      changePassword,
      logout
    }),
    [
      user,
      changePassword,
      login,
      logout
    ]
  );

  return <AuthProvider value={values}>{children}</AuthProvider>;
};
