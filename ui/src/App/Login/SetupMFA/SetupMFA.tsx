import { useAuth } from 'core/Auth';
import { FC, useCallback, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate } from 'react-router-dom';
import { useMount } from 'react-use';
import { QRCode } from 'shared/elements/QRCode';
import { AuthCode } from 'shared/form/AuthCode';

import css from './SetupMFA.module.css';
import { setupMFA } from 'core/API/auth';

export const SetupMFA: FC = () => {
  const [totpCode, setTotpCode] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const { user } = useAuth();

  // TODO: Hookup backend
  const getTOTPCode = useCallback(async () => {
    // TODO: Get OTP MFA code
    try {
      const res = await setupMFA({
        command: 'setup'
      });
      setTotpCode(res.data.data.totp_uri);
    } catch (error) {
      console.log(error);
    }
  }, []);

  useMount(() => {
    getTOTPCode();
  });

  const verifyTOTPCode = useCallback(async (val: string) => {
    try {
      await setupMFA({
        command: 'verify',
        mfa_token: val
      });
    } catch (error) {
      console.log(error);
    }
  }, []);

  if (!user?.needs_mfa) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Setup MFA</title>
      </Helmet>
      <div className={css.container}>
        <h1>Setup MFA</h1>
        <QRCode value={totpCode} />
        <br />
        <br />
        <h3>Enter Code</h3>
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
