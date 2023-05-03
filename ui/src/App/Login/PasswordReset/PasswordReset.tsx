import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ResetPassword } from './components/ResetPassword';
import { ForgotPassword } from './components/ForgotPassword';
import { ReactComponent as Logo } from 'assets/brand/mark.svg';
import styles from './PasswordReset.module.css';

export const PasswordReset = () => {
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get('token'), [searchParams]);

  return (
    <div className={styles.container}>
      <Logo height={55} width={55} />
      {token ? <ResetPassword token={token} /> : <ForgotPassword />}
    </div>
  );
};
