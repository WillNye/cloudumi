import { FC } from 'react';
import { Helmet } from 'react-helmet-async';

import css from './Dashboard.module.css';

const Dashboard: FC = () => {
  return (
    <>
      <Helmet>
        <title>Dashboard</title>
      </Helmet>
      <div className={css.container}>
        <h1>Welcome to NOQ</h1>
      </div>
    </>
  );
};

export default Dashboard;
