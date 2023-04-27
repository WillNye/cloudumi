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
import { ReactComponent as Logo } from 'assets/brand/mark.svg';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { LineBreak } from 'shared/elements/LineBreak';
import styles from './CompletePassword.module.css';

const completePasswordSchema = Yup.object().shape({
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
    resolver: yupResolver(completePasswordSchema),
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
        await completePassword({
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
        <title>Complete Password</title>
      </Helmet>
      <div className={styles.container}>
        <Logo height={55} width={55} />
        <h2 className={styles.title}>Set New Password</h2>

        <p className={styles.description}>
          Your current password was provided for your initial login. To ensure
          the security of your account, please create a new password before
          proceeding with access to your account.
        </p>

        <div className={styles.box}>
          <form onSubmit={handleSubmit(onSubmit)}>
            <Block label="Current Password" disableLabelPadding>
              <Input
                type="password"
                autoCapitalize="none"
                autoCorrect="off"
                placeholder="Current password"
                fullWidth
                {...register('currentPassword')}
              />
            </Block>
            <LineBreak />

            <Block label="New Password" disableLabelPadding>
              <Input
                type="password"
                autoCapitalize="none"
                autoCorrect="off"
                placeholder="New password"
                fullWidth
                {...register('newPassword')}
              />
            </Block>
            <PasswordMeter value={passwordValue} />
            <LineBreak />

            <Block label="Confirm Password" disableLabelPadding>
              <Input
                type="password"
                autoCapitalize="none"
                autoCorrect="off"
                placeholder="Confirm password"
                fullWidth
                {...register('confirmNewPassword')}
              />
            </Block>
            {errors?.confirmNewPassword && touchedFields.confirmNewPassword && (
              <p>{errors.confirmNewPassword.message}</p>
            )}
            <LineBreak />

            {errorMessage && (
              <Notification
                type={NotificationType.ERROR}
                header={errorMessage}
                fullWidth
                showCloseIcon={false}
              />
            )}

            <Button type="submit" disabled={isSubmitting || !isValid} fullWidth>
              {isSubmitting ? 'Resetting Password...' : 'Reset Password'}
            </Button>
          </form>
        </div>
      </div>
    </>
  );
};
