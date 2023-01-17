import { FC, PropsWithChildren } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';

export const AuthRoute: FC<PropsWithChildren> = props => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.password_reset_required) {
    return <Navigate to="/login/complete-password" replace />;
  }

  if (user.mfa_setup_required) {
    return <Navigate to="/login/setup-mfa" replace />;
  }

  if (user.mfa_verification_required) {
    return <Navigate to="/login/mfa" replace />;
  }

  return <Outlet />;
};
