import { useAuth } from 'core/Auth';
import { AuthenticationFlowType } from 'core/Auth/constants';
import { FC, useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Navigate } from 'react-router-dom';
import { QRCode } from 'shared/elements/QRCode';
import { AuthCode } from 'shared/form/AuthCode';

import css from './SetupMFA.module.css';

export const SetupMFA: FC = () => {
  const [totpCode, setTotpCode] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const { setupTOTP, verifyTotpToken, user } = useAuth();

  // TODO: Hookup backend

  const getTOTPCode = useCallback(async () => {
    const code = await setupTOTP();
    setTotpCode(code);
  }, [setupTOTP]);

  useEffect(function onMount() {
    getTOTPCode();
  }, []);

  const verifyTOTPCode = useCallback(
    async (val: string) => {
      await verifyTotpToken(val);
    },
    [verifyTotpToken]
  );

  if (
    user?.authenticationFlowType !== AuthenticationFlowType.USER_SRP_AUTH ||
    user?.preferredMFA !== 'NOMFA'
  ) {
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
