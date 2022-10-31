import { FC, PropsWithChildren } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { ChallengeName, AuthenticationFlowType } from './constants';

export const AuthRoute: FC<PropsWithChildren> = props => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.challengeName === ChallengeName.NEW_PASSWORD_REQUIRED) {
    return <Navigate to="/login/complete-password" replace />;
  }

  if (user.challengeName === ChallengeName.SOFTWARE_TOKEN_MFA) {
    return <Navigate to="/login/mfa" replace />;
  }

  if (
    user.authenticationFlowType === AuthenticationFlowType.USER_SRP_AUTH &&
    user.preferredMFA === 'NOMFA'
  ) {
    return <Navigate to="/login/setup-mfa" replace />;
  }

  return <Outlet />;
};
