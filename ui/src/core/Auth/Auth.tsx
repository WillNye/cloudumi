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

import { getTenantUserpool } from '../API/tenant';
import '../AWS/Amplify';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isCheckingUser, setIsCheckingUser] = useState(true);
  const [isValidTenant, setIsValidTenant] = useState(true);
  const navigate = useNavigate();

  useEffect(function onMount() {
    configureTenantOnMount();
  }, []);

  const configureTenantOnMount = async () => {
    setIsCheckingUser(true);
    getTenantUserpool()
      .then(async res => {
        setIsValidTenant(true);

        // configure amplify based on tenant user pool details
        // Currently disable because backend development user pool requires a secret that is not supported in Amplify
        // updateAmplifyConfig(res.data);

        await getAuthenticatedUser();
      })
      .catch(error => {
        setIsValidTenant(false);
      })
      .finally(() => {
        setIsCheckingUser(false);
      });
  };

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

  if (!isValidTenant) {
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
