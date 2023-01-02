import { useAuth } from 'core/Auth';
import { FC, useCallback, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate } from 'react-router-dom';
import { AuthCode } from 'shared/form/AuthCode';
import css from './MFA.module.css';
import { setupMFA } from 'core/API/auth';

export const MFA: FC = () => {
  const { user, getUser } = useAuth();

  const verifyTOTPCode = useCallback(
    async (val: string) => {
      try {
        await setupMFA({
          command: 'verify',
          mfa_token: val
        });
        await getUser();
      } catch (error) {
        console.log(error);
      }
    },
    [getUser]
  );
  if (user?.mfa_setup_required) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>MFA</title>
      </Helmet>
      <div className={css.container}>
        <h1>MFA</h1>
        {/* TODO (Kayizzi) - MFA text appears black in Chrome and it is hard to read */}
        {/* TODO (Kayizzi) - MFA component needs to return error on invalid MFA */}
        <AuthCode
          onChange={val => {
            if (val?.length === 6) {
              // TODO (Kayizzi) - If invalid MFA is entered , often times the user cannot retry
              // because the session has already been used. We need to handle this and get a new session
              // {"__type":"NotAuthorizedException","message":"Invalid session for the user, session can only be used once."}
              verifyTOTPCode(val);
            }
          }}
        />
      </div>
    </>
  );
};
