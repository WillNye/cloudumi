import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { useCallback, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { Block } from 'shared/layout/Block';
import { Button } from 'shared/elements/Button';
import { Input } from 'shared/form/Input';
import { resetPassword } from 'core/API/auth';
import { LineBreak } from 'shared/elements/LineBreak';
import styles from '../PasswordReset.module.css';

const DEFAULT_SUCCESS_MSG =
  // eslint-disable-next-line max-len
  'If your user exists, we have sent you an email with a password reset link that is valid for 15 minutes. Please check your email to reset your password.';

const emailSchema = Yup.object().shape({
  email: Yup.string().email('Invalid email').required('Required')
});

export const ForgotPassword = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors, isValid, touchedFields }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(emailSchema),
    defaultValues: {
      email: ''
    }
  });

  const onSubmit = useCallback(async ({ email }) => {
    setSuccessMessage(null);
    setErrorMessage(null);
    try {
      const res = await resetPassword({
        command: 'request',
        email
      });
      const resData = res?.data?.data;
      const successMg = resData?.message || DEFAULT_SUCCESS_MSG;
      setSuccessMessage(successMg);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(errorMsg || 'An error occurred while resetting Password');
    }
  }, []);

  return (
    <>
      <h2 className={styles.title}>Forgot password</h2>
      <p className={styles.description}>
        Forgot your password? No problem. Enter your email address to receive a
        link to reset it. Contact our support team if you need further
        assistance.
      </p>
      <div className={styles.box}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Block label="Email" disableLabelPadding>
            <Input
              type="text"
              autoCapitalize="none"
              autoCorrect="off"
              placeholder="Email"
              {...register('email')}
            />
          </Block>
          {errors?.email && touchedFields.email && (
            <p>{errors.email.message}</p>
          )}
          <LineBreak size="small" />
          {successMessage && (
            <Notification
              type={NotificationType.SUCCESS}
              header={successMessage}
              showCloseIcon={false}
            />
          )}
          {errorMessage && (
            <Notification
              type={NotificationType.ERROR}
              header={errorMessage}
              showCloseIcon={false}
            />
          )}
          <LineBreak size="small" />
          <Button type="submit" fullWidth disabled={isSubmitting || !isValid}>
            Reset Password
          </Button>
        </form>
      </div>
    </>
  );
};
