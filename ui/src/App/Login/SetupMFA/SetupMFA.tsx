import { useAuth } from 'core/Auth';
import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate, useNavigate } from 'react-router-dom';
import { QRCode } from 'shared/elements/QRCode';
import { AuthCode } from 'shared/form/AuthCode';
import { ReactComponent as Logo } from 'assets/brand/mark.svg';
import { SetupMFAParams, setupMFA } from 'core/API/auth';
import { extractErrorMessage } from 'core/API/utils';
import { AxiosError } from 'axios';
import { Loader } from 'shared/elements/Loader';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { LineBreak } from 'shared/elements/LineBreak';

import styles from './SetupMFA.module.css';
import { useMutation } from '@tanstack/react-query';

export const SetupMFA: FC = () => {
  const [totpCode, setTotpCode] = useState<Record<string, string>>();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittingError, setSubmittingError] = useState<string | null>(null);

  const { user, getUser } = useAuth();

  const navigate = useNavigate();

  const { mutateAsync: setupMFAMutation } = useMutation({
    mutationFn: (formData: SetupMFAParams) => setupMFA(formData),
    mutationKey: ['setupMFA']
  });

  const isMounted = useRef(false);

  const mfaSetupRequired = useMemo(() => user?.mfa_setup_required, [user]);

  const getTOTPCode = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await setupMFAMutation({
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
  }, [setupMFAMutation]);

  useEffect(() => {
    if (!isMounted.current && mfaSetupRequired) {
      isMounted.current = true;
      getTOTPCode();
    }
  }, [isMounted, mfaSetupRequired, getTOTPCode]);

  const verifyTOTPCode = useCallback(
    async (val: string) => {
      setIsSubmitting(true);
      try {
        await setupMFAMutation({
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
    [getUser, navigate, setupMFAMutation]
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
      <div className={styles.container}>
        {isLoading ? (
          <Loader fullPage />
        ) : (
          <>
            <Logo height={55} width={55} />
            <h2 className={styles.title}>Setup MFA</h2>
            <p className={styles.description}>
              Scan the QR code to enable Multi-Factor Authentication and add an
              extra layer of security to your account.
            </p>
            <LineBreak />
            <QRCode value={totpCode?.totp_uri ?? ''} />
            <LineBreak />
            <div>or use manual code</div>
            <div className={styles.box} data-testid="manual-code">
              <pre>{totpCode?.mfa_secret}</pre>
            </div>
            <LineBreak />
            <h3>Enter Code</h3>
            <LineBreak />
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
              <>
                <LineBreak />
                <Notification
                  type={NotificationType.ERROR}
                  header={submittingError}
                  showCloseIcon={false}
                />
              </>
            )}
            <LineBreak size="large" />
            <h4 className={styles.stepsHeader}>Steps to setup MFA</h4>
            <div className={styles.steps}>
              <ol>
                <li>
                  Download the Google Authenticator or Authy app from the App
                  Store or Google Play Store.
                </li>
                <li>Open the app and choose to add a new account.</li>
                <li>
                  Choose &apos;Scan QR code&apos; and scan the QR code displayed
                  below.
                </li>
                <li>
                  After scanning, the app will display a temporary 6-digit code.
                  Enter this code in the field above.
                </li>
              </ol>
            </div>
          </>
        )}
      </div>
    </>
  );
};
