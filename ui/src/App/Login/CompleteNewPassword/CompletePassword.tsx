import { useAuth } from 'core/Auth';
import { FC, useCallback } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import { Navigate } from 'react-router-dom';
import css from './CompletePassword.module.css';
import { Input } from 'shared/form/Input';
import { Button } from 'shared/elements/Button';
import { Block } from 'shared/layout/Block';
import { completePassword } from 'core/API/auth';

const comletePasswordSchema = Yup.object().shape({
  newPassword: Yup.string().required('Required'),
  currentPassword: Yup.string().required('Required'),
  confirmNewPassword: Yup.string()
    .required('Required')
    .oneOf([Yup.ref('newPassword')], 'Passwords must match')
});

export const CompleteNewPassword: FC = () => {
  const { user, getUser } = useAuth();

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
      currentPassword: '',
      confirmNewPassword: ''
    }
  });

  const passwordValue = watch('newPassword');

  const onSubmit = useCallback(
    async ({ newPassword, currentPassword }) => {
      // TODO: Setup new password
      completePassword;

      try {
        const res = await completePassword({
          new_password: newPassword,
          current_password: currentPassword
        });
        await getUser();
      } catch (error) {
        // handle login errors
      }
    },
    [getUser]
  );

  if (!user?.password_reset_required) {
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
          <Block label="Current Password" disableLabelPadding>
            <Input
              type="password"
              autoCapitalize="none"
              autoCorrect="off"
              placeholder="Current password"
              {...register('currentPassword')}
            />
          </Block>
          <br />
          <Block label="New Password" disableLabelPadding>
            <Input
              type="password"
              autoCapitalize="none"
              autoCorrect="off"
              placeholder="New password"
              {...register('newPassword')}
            />
          </Block>
          <PasswordMeter value={passwordValue} />
          <br />
          <Block label="Confirm Password" disableLabelPadding>
            <Input
              type="password"
              autoCapitalize="none"
              autoCorrect="off"
              placeholder="Confirm password"
              {...register('confirmNewPassword')}
            />
          </Block>
          {errors?.confirmNewPassword && touchedFields.confirmNewPassword && (
            <p>{errors.confirmNewPassword.message}</p>
          )}
          <br />
          <br />
          <Button type="submit" disabled={isSubmitting || !isValid}>
            {isSubmitting ? 'Resetting Password...' : 'Reset Password'}
          </Button>
        </form>
      </div>
    </>
  );
};
