import { createContext, useContext } from 'react';

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
  logout: () => void;
}

export const AuthContext = createContext<AuthContextProps>({
  login: async () => undefined,
  logout: async () => undefined,
  changePassword: async () => undefined,
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
