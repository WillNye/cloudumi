import { useAuth } from 'core/Auth';
import { ChallengeName } from 'core/Auth/constants';
import { FC, useCallback, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate } from 'react-router-dom';
import { AuthCode } from 'shared/form/AuthCode';
import css from './MFA.module.css';

export const MFA: FC = () => {
  const { confirmSignIn, user } = useAuth();

  const verifyTOTPCode = useCallback(
    async (val: string) => {
      await confirmSignIn(val);
    },
    [confirmSignIn]
  );

  if (user?.challengeName !== ChallengeName.SOFTWARE_TOKEN_MFA) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>MFA</title>
      </Helmet>
      <div className={css.container}>
        <h1>MFA</h1>
        <AuthCode
          onChange={val => {
            if (val?.length === 6) {
              verifyTOTPCode(val);
            }
          }}
        />
      </div>
    </>
  );
};
