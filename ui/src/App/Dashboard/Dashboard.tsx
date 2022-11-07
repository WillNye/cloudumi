import { useAuth } from 'core/Auth';
import { FC } from 'react';
import { Helmet } from 'react-helmet-async';

import css from './Dashboard.module.css';

const Dashboard: FC = () => {
  const { logout } = useAuth();

  return (
    <>
      <Helmet>
        <title>Dashboard</title>
      </Helmet>
      <div className={css.container}>
        <h1>Welcome to NOQ</h1>

        <button onClick={logout}></button>
      </div>
    </>
  );
};

export default Dashboard;
