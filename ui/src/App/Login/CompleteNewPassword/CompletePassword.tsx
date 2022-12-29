import { useAuth } from 'core/Auth';
import { FC, useCallback } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import { Navigate } from 'react-router-dom';
import { ChallengeName } from 'core/Auth/constants';
import css from './CompletePassword.module.css';

const comletePasswordSchema = Yup.object().shape({
  newPassword: Yup.string().required('Required'),
  confirmNewPassword: Yup.string()
    .required('Required')
    .oneOf([Yup.ref('newPassword')], 'Passwords must match')
});

export const CompleteNewPassword: FC = () => {
  const { user } = useAuth();

  const {
    register,
    watch,
    handleSubmit,
    formState: { isSubmitting, isValid, errors, touchedFields }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(comletePasswordSchema),
    defaultValues: {
      newPassword: '',
      confirmNewPassword: ''
    }
  });

  const passwordValue = watch('newPassword');

  const onSubmit = useCallback(async ({ newPassword }) => {
    // TODO: Setup new password
  }, []);

  if (user?.challengeName !== ChallengeName.NEW_PASSWORD_REQUIRED) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Complete Password</title>
      </Helmet>
      <div className={css.container}>
        <h1>Complete Password</h1>
        <form onSubmit={handleSubmit(onSubmit)}>
          <br />
          <input
            type="password"
            autoCapitalize="none"
            autoCorrect="off"
            {...register('newPassword')}
          />
          <PasswordMeter value={passwordValue} />
          <br />
          <input
            type="password"
            autoCapitalize="none"
            autoCorrect="off"
            {...register('confirmNewPassword')}
          />
          {errors?.confirmNewPassword && touchedFields.confirmNewPassword && (
            <p>{errors.confirmNewPassword.message}</p>
          )}
          <br />
          <br />
          <button type="submit" disabled={isSubmitting || !isValid}>
            {isSubmitting ? 'Resetting Password...' : 'Reset Password'}
          </button>
        </form>
      </div>
    </>
  );
};
