import { createContext, useContext } from 'react';
import { User } from './types';

export interface AuthLoginInputs {
  username: string;
  password: string;
}

export interface AuthResetPasswordInputs {
  oldPassword: string;
  newPassword: string;
}

export interface AuthContextProps {
  login: (input: AuthLoginInputs) => void;
  changePassword: (input: AuthResetPasswordInputs) => void;
  completeNewPassword: (input: string) => void;
  verifyTotpToken: (input: string) => void;
  confirmSignIn: (input: string) => void;
  logout: () => void;
  setupTOTP: () => Promise<string>;
  user: User | null;
}

export const AuthContext = createContext<AuthContextProps>({
  user: null,
  login: async () => undefined,
  logout: async () => undefined,
  changePassword: async () => undefined,
  completeNewPassword: async () => undefined,
  setupTOTP: async () => undefined,
  verifyTotpToken: async () => undefined,
  confirmSignIn: async () => undefined
});

export const { Provider: AuthProvider, Consumer: AuthConsumer } = AuthContext;

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error(
      '`useAuth` hook must be used within a `AuthProvider` component'
    );
  }

  return context;
};
