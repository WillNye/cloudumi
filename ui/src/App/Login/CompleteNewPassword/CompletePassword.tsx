import { useAuth } from 'core/Auth';
import { FC, useCallback, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import { Navigate } from 'react-router-dom';
import { Input } from 'shared/form/Input';
import { Button } from 'shared/elements/Button';
import { Block } from 'shared/layout/Block';
import { completePassword } from 'core/API/auth';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';
import css from './CompletePassword.module.css';

const comletePasswordSchema = Yup.object().shape({
  newPassword: Yup.string().required('Required'),
  currentPassword: Yup.string().required('Required'),
  confirmNewPassword: Yup.string()
    .required('Required')
    .oneOf([Yup.ref('newPassword')], 'Passwords must match')
});

export const CompleteNewPassword: FC = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
      try {
        const res = await completePassword({
          new_password: newPassword,
          current_password: currentPassword
        });
        await getUser();
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while reseting Password'
        );
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
        <title>Reset Password</title>
      </Helmet>
      <div className={css.container}>
        <h1>Reset Password</h1>
        <br />
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
          {errorMessage && (
            <Notification
              type={NotificationType.ERROR}
              header={errorMessage}
              showCloseIcon={false}
            />
          )}
          <br />
          <Button type="submit" disabled={isSubmitting || !isValid} fullWidth>
            {isSubmitting ? 'Resetting Password...' : 'Reset Password'}
          </Button>
        </form>
      </div>
    </>
  );
};
