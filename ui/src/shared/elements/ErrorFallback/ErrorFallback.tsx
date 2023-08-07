import { FC, useCallback, useMemo } from 'react';
import classNames from 'classnames';
import styles from './ErrorFallback.module.css';
import CloudImage from '../../../assets/illustrations/cloud.svg';
import { Button } from '../Button';
import { LineBreak } from '../LineBreak';
import { useNavigate } from 'react-router-dom';

interface ErrorFallbackProps {
  fullPage?: boolean;
  className?: string;
}

export const ErrorFallback: FC<ErrorFallbackProps> = ({
  className,
  fullPage = false
}) => {
  const navigate = useNavigate();

  const classes = useMemo(
    () =>
      classNames(styles.error, {
        [styles.fullPage]: fullPage
      }),
    [fullPage]
  );

  const handleReload = useCallback(() => {
    window.location.reload();
  }, []);

  const handleHome = useCallback(() => {
    navigate('/');
  }, [navigate]);

  return (
    <div className={`${className} ${classes}`}>
      <img src={CloudImage} />
      <LineBreak size="large" />
      <h2>Error</h2>
      <LineBreak />
      <p className={styles.description}>
        Sorry, an error has occurred. Our team has been notified of the issue
        and is working to resolve it as soon as possible. Please try again
        later.
      </p>
      <LineBreak size="large" />
      <div className={styles.resetButtons}>
        <Button
          color="secondary"
          size="small"
          variant="outline"
          onClick={handleReload}
        >
          Reload
        </Button>
        <Button size="small" onClick={handleHome}>
          Home
        </Button>
      </div>
    </div>
  );
};
