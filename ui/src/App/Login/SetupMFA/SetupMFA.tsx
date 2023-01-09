import { useAuth } from 'core/Auth';
import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate, useNavigate } from 'react-router-dom';
import { QRCode } from 'shared/elements/QRCode';
import { AuthCode } from 'shared/form/AuthCode';

import css from './SetupMFA.module.css';
import { setupMFA } from 'core/API/auth';
import { extractErrorMessage } from 'core/API/utils';
import { AxiosError } from 'axios';
import { Loader } from 'shared/elements/Loader';
import { Notification, NotificationType } from 'shared/elements/Notification';

export const SetupMFA: FC = () => {
  const [totpCode, setTotpCode] = useState<Record<string, string>>();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittingError, setSubmittingError] = useState<string | null>(null);

  const { user, getUser } = useAuth();

  const navigate = useNavigate();

  const isMounted = useRef(false);

  const mfaSetupRequired = useMemo(() => user?.mfa_setup_required, [user]);

  useEffect(() => {
    if (!isMounted.current && mfaSetupRequired) {
      isMounted.current = true;
      getTOTPCode();
    }
  }, [isMounted, mfaSetupRequired]);

  const getTOTPCode = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await setupMFA({
        command: 'setup'
      });
      setTotpCode(res.data.data);
      setIsLoading(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(errorMsg || 'Unable to setup MFA');
      setIsLoading(false);
    }
  }, []);

  const verifyTOTPCode = useCallback(
    async (val: string) => {
      setIsSubmitting(true);
      try {
        await setupMFA({
          command: 'verify',
          mfa_token: val
        });
        await getUser();
        setIsSubmitting(false);
        navigate('/');
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setSubmittingError(errorMsg || 'Unable to setup MFA');
        setIsSubmitting(false);
      }
    },
    [getUser, navigate]
  );

  if (errorMessage) {
    // setup Generic Error component
  }

  if (!mfaSetupRequired) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Setup MFA</title>
      </Helmet>
      <div className={css.container}>
        {isLoading ? (
          <Loader fullPage />
        ) : (
          <>
            <h1>Setup MFA</h1>
            <QRCode value={totpCode?.totp_uri ?? ''} />
            <br />
            <div>{totpCode?.mfa_secret}</div>
            <br />
            <h3>Enter Code</h3>
            <AuthCode
              disabled={isSubmitting}
              onChange={val => {
                setSubmittingError(null);
                if (val?.length === 6) {
                  verifyTOTPCode(val);
                }
              }}
            />
            {submittingError && (
              <Notification
                type={NotificationType.ERROR}
                header={submittingError}
                showCloseIcon={false}
              />
            )}
          </>
        )}
      </div>
    </>
  );
};
