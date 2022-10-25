import { FC } from 'react';
import { Helmet } from 'react-helmet-async';
import css from './ChangePassword.module.css';

export const ChangePassword: FC = () => {
  // TODO: Add form to change password
  // NOTE: We will come back later and add password complexity/checker

  return (
    <>
      <Helmet>
        <title>Change Password</title>
      </Helmet>
      <div className={css.container}>
        <h1>Change Password</h1>
        TODO
      </div>
    </>
  );
};
