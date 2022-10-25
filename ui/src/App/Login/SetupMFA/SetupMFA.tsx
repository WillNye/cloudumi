import { FC } from 'react';
import { Helmet } from 'react-helmet-async';
import { QRCode } from 'shared/elements/QRCode';
import css from './SetupMFA.module.css';

export const SetupMFA: FC = () => {
  // TODO: Hookup backend

  return (
    <>
      <Helmet>
        <title>Setup MFA</title>
      </Helmet>
      <div className={css.container}>
        <h1>Setup MFA</h1>
        <QRCode value="make me real" />
      </div>
    </>
  );
};
