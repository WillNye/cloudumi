import { createContext, useContext } from 'react';

export interface AuthContextProps {
  login: () => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextProps>({
  login: () => undefined,
  logout: async () => undefined
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
