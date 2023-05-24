import { FC, PropsWithChildren } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';

const AdminAuthRoute: FC<PropsWithChildren> = () => {
  const { user } = useAuth();

  if (!user?.is_admin) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};

export default AdminAuthRoute;
