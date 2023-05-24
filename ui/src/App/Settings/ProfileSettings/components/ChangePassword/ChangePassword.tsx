import { Button } from 'shared/elements/Button';
import { Input } from 'shared/form/Input';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import { useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { CompletePasswordParams, completePassword } from 'core/API/auth';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Block } from 'shared/layout/Block';
import { LineBreak } from 'shared/elements/LineBreak';
import { Segment } from 'shared/layout/Segment';
import { toast } from 'react-toastify';

const changePasswordSchema = Yup.object().shape({
  currentPassword: Yup.string().required('Required'),
  newPassword: Yup.string().required('Required'),
  confirmNewPassword: Yup.string()
    .required('Required')
    .oneOf([Yup.ref('newPassword')], 'Passwords must match')
});

const ChangePassword = () => {
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
      currentPassword: '',
      newPassword: '',
      confirmNewPassword: ''
    }
  });

  const { mutateAsync: completePasswordMutation } = useMutation({
    mutationFn: (data: CompletePasswordParams) => completePassword(data)
  });

  const passwordValue = watch('newPassword');

  const onSubmit = useCallback(
    async ({ newPassword, currentPassword }) => {
      try {
        await completePasswordMutation({
          new_password: newPassword,
          current_password: currentPassword
        });
        toast.success('Successfully updated user password');
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        toast.error(errorMsg || 'An error occurred while reseting Password');
      }
    },
    [completePasswordMutation]
  );

  return (
    <Segment>
      <LineBreak size="large" />

      <form onSubmit={handleSubmit(onSubmit)}>
        <Block disableLabelPadding label="Current Password" />
        <Input
          type="password"
          autoCapitalize="none"
          autoCorrect="off"
          size="small"
          {...register('currentPassword')}
        />
        <LineBreak />
        <Block label="New Password" disableLabelPadding />
        <Input
          type="password"
          autoCapitalize="none"
          size="small"
          autoCorrect="off"
          {...register('newPassword')}
        />
        <PasswordMeter value={passwordValue} fullWidth />
        <LineBreak />
        <Block label="Confirm Password" disableLabelPadding />
        <Input
          type="password"
          autoCapitalize="none"
          size="small"
          autoCorrect="off"
          {...register('confirmNewPassword')}
        />
        {errors?.confirmNewPassword && touchedFields.confirmNewPassword && (
          <p>{errors.confirmNewPassword.message}</p>
        )}
        <LineBreak />
        <Button type="submit" disabled={isSubmitting || !isValid} size="small">
          {isSubmitting ? 'Resetting Password...' : 'Reset Password'}
        </Button>
      </form>
    </Segment>
  );
};

export default ChangePassword;
