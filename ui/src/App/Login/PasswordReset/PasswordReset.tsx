import { useMemo } from 'react';
import css from './PasswordReset.module.css';
import { useSearchParams } from 'react-router-dom';
import { SetNewPassword } from './components/SetNewPassword';
import { ResetPassword } from './components/ResetPassword';

export const PasswordReset = () => {
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get('token'), [searchParams]);

  return (
    <div className={css.container}>
      <h3>Reset Password</h3>
      <br />
      {token ? <SetNewPassword token={token} /> : <ResetPassword />}
    </div>
  );
};
