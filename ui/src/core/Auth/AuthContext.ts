import { Dispatch, createContext, useContext } from 'react';
import { User } from './types';
import { QueryObserverResult } from '@tanstack/react-query';

export interface AuthLoginInputs {
  username: string;
  password: string;
}

export interface AuthResetPasswordInputs {
  oldPassword: string;
  newPassword: string;
}

export interface AuthContextProps {
  user: User | null;
  isHubAccountInstalled: boolean;
  isGithubInstalled: boolean;
  setUser: Dispatch<User | null>;
  getUser: () => Promise<QueryObserverResult<any, unknown>>;
}

export const AuthContext = createContext<AuthContextProps>({
  user: null,
  isHubAccountInstalled: true,
  isGithubInstalled: true,
  setUser: () => undefined,
  getUser: () => undefined
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
