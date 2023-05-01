import { useAuth } from 'core/Auth';
import { FC, useCallback, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate, useNavigate } from 'react-router-dom';
import { AuthCode } from 'shared/form/AuthCode';
import { verifyMFA } from 'core/API/auth';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { ReactComponent as Logo } from 'assets/brand/mark.svg';
import { LineBreak } from 'shared/elements/LineBreak';

import styles from './MFA.module.css';

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
      <div className={styles.container}>
        <Logo height={55} width={55} />
        <h2 className={styles.title}>MFA Verification</h2>
        <p className={styles.description}>
          Secure your account with Multi-Factor Authentication. Enter your
          unique verification code to log in securely.
        </p>
        <LineBreak size="large" />
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
        <LineBreak />
        {errorMessage && (
          <Notification
            type={NotificationType.ERROR}
            header={errorMessage}
            showCloseIcon={false}
          />
        )}
        <LineBreak size="large" />
        <div className={styles.warning}>
          Warning: If you are unable to login with Multi-Factor Authentication,
          please contact an administrator from your company. Do not attempt to
          disable or bypass MFA as it could compromise the security of your
          account.
        </div>
      </div>
    </>
  );
};
