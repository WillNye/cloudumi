import { Dispatch, createContext, useContext } from 'react';
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
  user: User | null;
  setUser: Dispatch<User | null>;
  getUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextProps>({
  user: null,
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
