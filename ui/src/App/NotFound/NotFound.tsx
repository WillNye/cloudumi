import { FC, useCallback, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import ErrorImage from '../../assets/illustrations/error.svg';
import css from './NotFound.module.css';
import { Button } from 'shared/elements/Button';
import classNames from 'classnames';
import { useNavigate } from 'react-router-dom';

interface NotFoundProps {
  fullPage?: boolean;
}

export const NotFound: FC<NotFoundProps> = ({ fullPage = false }) => {
  const navigate = useNavigate();

  const classes = useMemo(
    () =>
      classNames(css.container, {
        [css.fullPage]: fullPage
      }),
    [fullPage]
  );

  const handleOnClick = useCallback(() => {
    navigate('/');
  }, [navigate]);

  return (
    <>
      <Helmet>
        <title>Not Found</title>
      </Helmet>
      <div className={classes}>
        <img src={ErrorImage} />
        <h2>Sorry, Page not found!</h2>
        <h5 className={css.text}>
          The page you are looking for could not be found.
        </h5>
        <Button
          variant="outline"
          color="secondary"
          size="medium"
          className={css.btn}
          onClick={handleOnClick}
        >
          Go Back to Home
        </Button>
      </div>
    </>
  );
};
