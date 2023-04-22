import { useAuth } from 'core/Auth';
import { FC, useCallback, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate, useNavigate } from 'react-router-dom';
import { AuthCode } from 'shared/form/AuthCode';
import css from './MFA.module.css';
import { verifyMFA } from 'core/API/auth';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';

export const MFA: FC = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { user, getUser } = useAuth();
  const navigate = useNavigate();

  const verifyTOTPCode = useCallback(
    async (val: string) => {
      setIsLoading(true);
      try {
        await verifyMFA({
          mfa_token: val
        });
        await getUser();
        setIsLoading(false);
        navigate('/');
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(errorMsg || 'An error occurred while logging in');
        setIsLoading(false);
      }
    },
    [getUser, navigate]
  );

  if (!user?.mfa_verification_required) {
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
        <br />
        <AuthCode
          disabled={isLoading}
          onChange={val => {
            setErrorMessage(null);
            if (val?.length === 6) {
              // TODO (Kayizzi) - If invalid MFA is entered , often times the user cannot retry
              // because the session has already been used. We need to handle this and get a new session
              verifyTOTPCode(val);
            }
          }}
        />
        <br />
        {errorMessage && (
          <Notification
            type={NotificationType.ERROR}
            header={errorMessage}
            showCloseIcon={false}
          />
        )}
      </div>
    </>
  );
};
