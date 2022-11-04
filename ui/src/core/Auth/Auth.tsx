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
import { useQuery } from '@apollo/client';
import { GetTenantUserPoolQuery, GET_TENANT_USERPOOL_QUERY } from 'core/graphql';
import '../AWS/Amplify';

export const Auth: FC<PropsWithChildren> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();
  const { loading, error: tenantError, data: tenantData } = useQuery<GetTenantUserPoolQuery>(GET_TENANT_USERPOOL_QUERY);

  useEffect(() => {
    // Configure amplify based on tenant user pool details
    // NOTE: Disabled due to cognito secret not supported by amplify
    // updateAmplifyConfig(tenantData);
  }, [tenantData]);

  const getAuthenticatedUser = useCallback(async () => {
    try {
      const user = await AmplifyAuth.currentAuthenticatedUser({
        bypassCache: false
      });
      const session = await AmplifyAuth.currentSession();
      setUser(user);
    } catch ({ message }) {
      throw new Error(`Error getting Authernticated user: ${message}`);
    }
  }, []);

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
    [user, getAuthenticatedUser, navigate]
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
    [user, getAuthenticatedUser, navigate]
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
    [user, getAuthenticatedUser, navigate]
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
    [user, getAuthenticatedUser, navigate]
  );

  const authBackend = useCallback(
    async () => {
      // Authenticate with the backend
      const session = await AmplifyAuth.currentSession();
      // Note on headers below - most browsers now implement Referrer Policy: strict-origin-when-cross-origin
      // and only specific headers are allowed: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy
      const res = await axios.post(`/api/v1/auth/cognito`, {jwtToken: session}, {  // TODO: this will have to be un-hardcoded
        headers: {
          'Content-Type': 'application/json',
        }, withCredentials: true
      })
    },[]
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
        const session = await AmplifyAuth.currentSession()
        if (session) {
          await setupAPIAuth(session)
        }
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

  // NOTE: I don't think we should put these 2 loading/invalid checks here
  if (loading) {
    // check is user data is available
    return <div>Loading...</div>;
  }

  if (!tenantError) {
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
