import {
  FC,
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState
} from 'react';
import axios from 'axios';
import { Auth as AmplifyAuth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';
import {
  AuthLoginInputs,
  AuthProvider,
  AuthResetPasswordInputs
} from './AuthContext';
import { ChallengeName } from './constants';
import { User } from './types';
import { CognitoUserSession } from "amazon-cognito-identity-js";

import '../AWS/Amplify';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isCheckingUser, setIsCheckingUser] = useState(true);
  const navigate = useNavigate();

  useEffect(function onMount() {
    getAuthenticatedUser().finally(() => {
      setIsCheckingUser(false);
    });
  }, []);

  const getAuthenticatedUser = async () => {
    try {
      const user = await AmplifyAuth.currentAuthenticatedUser({
        bypassCache: true
      });
      setUser(user);
    } catch ({ message }) {
      throw new Error(`Error getting Authernticated user: ${message}`);
    }
  };

  const setupTOTP = useCallback(async () => {
    try {
      const code = await AmplifyAuth.setupTOTP(user);
      // Dynamically get the issuer
      const username = user.attributes.email;
      const totpCode = `otpauth://totp/AWSCognito:${username}?secret=${code}&issuer=NOQ`;
      return totpCode;
    } catch ({ message }) {
      throw new Error(`Error getting TOTP code: ${message}`);
    }
  }, [user]);

  const resetMFA = useCallback(async () => {
    try {
      await AmplifyAuth.setPreferredMFA(user, 'NOMFA');
    } catch ({ message }) {
      throw new Error(`Error resetting MFA: ${message}`);
    }
  }, [user]);

  const verifyTotpToken = useCallback(
    async (challengeAnswer: string) => {
      try {
        // Then you will have your TOTP account in your TOTP-generating app (like Google Authenticator)
        // Use the generated one-time password to verify the setup
        await AmplifyAuth.verifyTotpToken(user, challengeAnswer);
        await AmplifyAuth.setPreferredMFA(user, 'TOTP');
        await getAuthenticatedUser();
        navigate('/');
      } catch ({ message }) {
        throw new Error(`Error setting up MFA: ${message}`);
      }


    },
    [user, navigate]
  );

  const confirmSignIn = useCallback(
    async (code: string) => {
      try {
        await AmplifyAuth.confirmSignIn(
          user, // Return object from Auth.signIn()
          code, // Confirmation code
          ChallengeName.SOFTWARE_TOKEN_MFA
        );
        await getAuthenticatedUser();
        navigate('/');
      } catch ({ message }) {
        throw new Error(`Error confirming signing in: ${message}`);
      }
      try {
        authBackend();
      } catch (error) {
        console.log(error);
      }    
    },
    [user, navigate]
  );

  const completeNewPassword = useCallback(
    async (newPassword: string) => {
      try {
        // Note: Not sure if we want to do this
        await AmplifyAuth.completeNewPassword(user, newPassword);
        await getAuthenticatedUser();

        // After login, we should redirect to the main page
        navigate('/');
      } catch ({ message }) {
        throw new Error(`Error changing password: ${message}`);
      }
    },
    [user, navigate]
  );

  const changePassword = useCallback(
    async ({ oldPassword, newPassword }: AuthResetPasswordInputs) => {
      try {
        // Note: Not sure if we want to do this
        await AmplifyAuth.changePassword(user, oldPassword, newPassword);
        await getAuthenticatedUser();

        // After login, we should redirect to the main page
        navigate('/');
      } catch ({ message }) {
        throw new Error(`Error changing password: ${message}`);
      }
    },
    [user, navigate]
  );

  const authBackend = useCallback(
    async () => {
      // Authenticate with the backend
      const session = await AmplifyAuth.currentSession();
      // Note on headers below - most browsers now implement Referrer Policy: strict-origin-when-cross-origin
      // and only specific headers are allowed: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy
      await axios.post(`http://localhost:8092/api/v1/auth/cognito`, {jwtToken: session}, {  // TODO: this will have to be un-hardcoded
        headers: {
          'Content-Type': 'application/json',
        }
      }).
        then(( res => {
          console.log(res);
        }))
      },
      []
    )

  const login = useCallback(
    async ({ username, password }: AuthLoginInputs) => {
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

      try {
        authBackend();
      } catch (error) {
        console.log(error);
      }
    },
    [navigate]
  );

  const logout = useCallback(async () => {
    try {
      await AmplifyAuth.signOut({ global: true });
      setUser(null);
      navigate('/login');
    } catch ({ message }) {
      throw new Error(`Error logging out: ${message}`);
    }
  }, [navigate]);

  const values = useMemo(
    () => ({
      user,
      login,
      changePassword,
      logout,
      completeNewPassword,
      verifyTotpToken,
      setupTOTP,
      confirmSignIn
    }),
    [
      user,
      changePassword,
      login,
      logout,
      completeNewPassword,
      verifyTotpToken,
      setupTOTP,
      confirmSignIn
    ]
  );

  if (isCheckingUser) {
    // check is user data is available
    return <div>Loading...</div>;
  }

  return <AuthProvider value={values}>{children}</AuthProvider>;
};
