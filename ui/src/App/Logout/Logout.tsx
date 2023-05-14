import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { logout } from 'core/API/auth';
import { useAuth } from 'core/Auth';
import { Navigate, useNavigate } from 'react-router-dom';
import { Loader } from 'shared/elements/Loader';
import errorSvg from '../../assets/illustrations/cloud.svg';
import styles from './Logout.module.css';

const Logout = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const navigate = useNavigate();

  const { setUser, user } = useAuth();

  useQuery({
    queryFn: logout,
    queryKey: ['logout'],
    onSuccess: () => {
      setUser(null);
      navigate('/login');
    },
    onError: () => {
      setErrorMessage('Oops! there was a problem, unable to log user out');
    },
    cacheTime: 0
  });

  if (!user) {
    return <Navigate to="login" />;
  }

  return (
    <div className={styles.container}>
      {errorMessage ? (
        <>
          <img src={errorSvg} height={320} />
          <h3 className={styles.title}>An error Occured</h3>
          <div className={styles.text}>{errorMessage}</div>
        </>
      ) : (
        <>
          <div>
            <Loader />
          </div>
          <h3 className={styles.title}>Just a moment...</h3>
          <div className={styles.text}>Attempting to log out</div>
        </>
      )}
    </div>
  );
};

export default Logout;
