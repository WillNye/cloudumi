import { Button } from 'shared/elements/Button';
import { Input } from 'shared/form/Input';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import { useCallback } from 'react';

const changePasswordSchema = Yup.object().shape({
  oldPassword: Yup.string().required('Required'),
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
      <h4>Change Password</h4>
      <br />

      <form onSubmit={handleSubmit(onSubmit)}>
        <Input
          type="password"
          autoCapitalize="none"
          autoCorrect="off"
          size="small"
          {...register('oldPassword')}
        />
        <br />

        <Input
          type="password"
          autoCapitalize="none"
          size="small"
          autoCorrect="off"
          {...register('newPassword')}
        />
        <PasswordMeter value={passwordValue} />
        <br />

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
        <br />
        <Button type="submit" disabled={isSubmitting || !isValid}>
          {isSubmitting ? 'Resetting Password...' : 'Reset Password'}
        </Button>
      </form>
    </>
  );
};

export default ChangePassword;
