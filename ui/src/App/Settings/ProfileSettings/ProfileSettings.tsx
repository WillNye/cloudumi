import { useAuth } from 'core/Auth';
import { FC, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { PasswordMeter } from 'shared/elements/PasswordMeter';
import css from './ProfileSettings.module.css';
import { Input } from 'shared/form/Input';
import { Button } from 'shared/elements/Button';

const changePasswordSchema = Yup.object().shape({
  oldPassword: Yup.string().required('Required'),
  newPassword: Yup.string().required('Required'),
  confirmNewPassword: Yup.string()
    .required('Required')
    .oneOf([Yup.ref('newPassword')], 'Passwords must match')
});

export const ProfileSettings: FC = () => {
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
      <div className={css.container}>
        <h4>Change Password</h4>
        <br />

        <form onSubmit={handleSubmit(onSubmit)}>
          <Input
            type="password"
            autoCapitalize="none"
            autoCorrect="off"
            {...register('oldPassword')}
          />
          <br />

          <Input
            type="password"
            autoCapitalize="none"
            autoCorrect="off"
            {...register('newPassword')}
          />
          <PasswordMeter value={passwordValue} />
          <br />

          <Input
            type="password"
            autoCapitalize="none"
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
      </div>
    </>
  );
};

export default ProfileSettings;
