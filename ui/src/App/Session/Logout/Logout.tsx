import { useAuth } from 'core/Auth';
import { FC, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import css from './Logout.module.css';
import { Navigate } from 'react-router-dom';

export const Logout: FC = () => {
  const { logout, user } = useAuth();

  useEffect(() => {
    const _logout = async () => {
      await logout();
    }

    _logout().catch(console.error)
  });

  if (!user) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Logout</title>
      </Helmet>
      <div className={css.container}>
        <h1>You&apos;ve been logged out</h1>
      </div>
    </>
  );
};
