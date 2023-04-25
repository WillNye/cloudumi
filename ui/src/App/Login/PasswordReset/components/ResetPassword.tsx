import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { FC, useCallback, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import { Block } from 'shared/layout/Block';
import { Button } from 'shared/elements/Button';
import { Input } from 'shared/form/Input';
import { resetPassword } from 'core/API/auth';
import { LineBreak } from 'shared/elements/LineBreak';
import styles from '../PasswordReset.module.css';

interface ResetPasswordProps {
  token: string;
}

const comletePasswordSchema = Yup.object().shape({
  newPassword: Yup.string().required('Required'),
  confirmNewPassword: Yup.string()
    .required('Required')
    .oneOf([Yup.ref('newPassword')], 'Passwords must match')
});

export const ResetPassword: FC<ResetPasswordProps> = ({ token }) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const navigate = useNavigate();

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

  const onSubmit = useCallback(
    async ({ newPassword }) => {
      try {
        await resetPassword({
          token,
          command: 'reset',
          password: newPassword
        });
        navigate('/login');
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while resetting Password'
        );
      }
    },
    [token, navigate]
  );

  return (
    <>
      <h2 className={styles.title}>Reset Password</h2>

      <p className={styles.description}>
        Welcome back! To reset your password, please enter a new password below.
        Be sure to choose a strong, unique password that you haven&apos;t used
        before.
      </p>
      <div className={styles.box}>
        <form onSubmit={handleSubmit(onSubmit)}>
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
          <LineBreak />
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
          <LineBreak />
          {errorMessage && (
            <Notification
              type={NotificationType.ERROR}
              header={errorMessage}
              showCloseIcon={false}
            />
          )}
          <LineBreak />
          <Button type="submit" fullWidth disabled={isSubmitting || !isValid}>
            Reset Password
          </Button>
        </form>
      </div>
    </>
  );
};
