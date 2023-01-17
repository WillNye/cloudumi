import { useAuth } from 'core/Auth';
import { FC, useCallback } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import css from './ChangePassword.module.css';

const changePasswordSchema = Yup.object().shape({
  oldPassword: Yup.string().required('Required'),
  newPassword: Yup.string().required('Required'),
  confirmNewPassword: Yup.string()
    .required('Required')
    .oneOf([Yup.ref('newPassword')], 'Passwords must match')
});

export const ChangePassword: FC = () => {
  const { user } = useAuth();

  const {
    register,
    watch,
    handleSubmit,
    formState: { isSubmitting, isValid, errors, touchedFields }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(changePasswordSchema),
    defaultValues: {
      oldPassword: '',
      newPassword: '',
      confirmNewPassword: ''
    }
  });

  const passwordValue = watch('newPassword');

  const onSubmit = useCallback(async ({ oldPassword, newPassword }) => {
    // TODO: Update password api route
  }, []);

  return (
    <>
      <Helmet>
        <title>Change Password</title>
      </Helmet>
      <div className={css.container}>
        <h1>Change Password</h1>
        <form onSubmit={handleSubmit(onSubmit)}>
          <input
            type="password"
            autoCapitalize="none"
            autoCorrect="off"
            {...register('oldPassword')}
          />
          <br />
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
