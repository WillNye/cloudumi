import { FC, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { AuthCode } from 'shared/form/AuthCode';
import css from './MFA.module.css';

export const MFA: FC = () => {
  // Note: Probably want to hook up the form here
  const [code, setCode] = useState<string>('');

  return (
    <>
      <Helmet>
        <title>MFA</title>
      </Helmet>
      <div className={css.container}>
        <h1>MFA</h1>
        <AuthCode
          onChange={val => {
            setCode(val);

            if (val?.length === 6) {
              // onSubmit(code);
            }
          }}
        />
      </div>
    </>
  );
};
