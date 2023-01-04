import { useAuth } from 'core/Auth';
import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate, useNavigate } from 'react-router-dom';
import { QRCode } from 'shared/elements/QRCode';
import { AuthCode } from 'shared/form/AuthCode';

import css from './SetupMFA.module.css';
import { setupMFA } from 'core/API/auth';

export const SetupMFA: FC = () => {
  const [totpCode, setTotpCode] = useState<Record<string, string>>();
  const [isLoading, setIsLoading] = useState<boolean>(false);

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

  // TODO: Hookup backend
  const getTOTPCode = useCallback(async () => {
    // TODO: Get OTP MFA code
    try {
      const res = await setupMFA({
        command: 'setup'
      });
      setTotpCode(res.data.data);
    } catch (error) {
      console.log(error);
    }
  }, []);

  const verifyTOTPCode = useCallback(
    async (val: string) => {
      try {
        await setupMFA({
          command: 'verify',
          mfa_token: val
        });
        await getUser();
        navigate('/');
      } catch (error) {
        console.log(error);
      }
    },
    [getUser, navigate]
  );

  if (!mfaSetupRequired) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Setup MFA</title>
      </Helmet>
      <div className={css.container}>
        <h1>Setup MFA</h1>
        <QRCode value={totpCode?.totp_uri ?? ''} />
        <br />
        <div>{totpCode?.mfa_secret}</div>
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
