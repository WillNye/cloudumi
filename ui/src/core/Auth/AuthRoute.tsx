import { FC, PropsWithChildren } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';

export const AuthRoute: FC<PropsWithChildren> = props => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // if (user.password_needs_reset) {
  //   return <Navigate to="/login/complete-password" replace />;
  // }

  // if (user.needs_mfa) {
  //   return <Navigate to="/login/mfa" replace />;
  // }

  // if (user.needs_mfa) {
  //   return <Navigate to="/login/setup-mfa" replace />;
  // }

  return <Outlet />;
};
