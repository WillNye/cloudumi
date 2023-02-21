import { FC, Fragment, useCallback, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Input } from 'shared/form/Input';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { updateUser } from 'core/API/settings';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import styles from './EditUserModal.module.css';
import { User } from '../../../types';

type EditUserModalProps = {
  canEdit: boolean;
  user: User;
};

const updatingUserSchema = Yup.object().shape({
  email: Yup.string().email().required('Required'),
  username: Yup.string().required('Required')
});

const EditUserModal: FC<EditUserModalProps> = ({ canEdit, user }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, isValid, errors, touchedFields }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(updatingUserSchema),
    defaultValues: {
      email: user.email,
      username: user.username
    }
  });

  const onSubmit = useCallback(
    async ({ email, username }) => {
      setErrorMessage(null);
      setSuccessMessage(null);
      try {
        await updateUser(
          {
            id: user.id,
            email,
            username
          },
          'update_user'
        );
        setSuccessMessage('Successfully updated user');
        // TODO refetch all users
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while updating new user'
        );
      }
    },
    [user.id]
  );

  if (!canEdit) {
    return <Fragment />;
  }

  return (
    <div className={styles.container}>
      <div className={styles.btn} onClick={() => setShowDialog(true)}>
        <Icon name="edit" size="medium" />
      </div>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        disablePadding
        header="Edit User Modal"
        size="medium"
      >
        <div className={styles.content}>
          <form onSubmit={handleSubmit(onSubmit)}>
            <Block disableLabelPadding label="Username" required></Block>
            <Input
              fullWidth
              placeholder="username"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('username')}
            />
            {errors?.username && touchedFields.username && (
              <p>{errors.username.message}</p>
            )}
            <br />
            <Block disableLabelPadding label="Email" required></Block>
            <Input
              fullWidth
              placeholder="email"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('email')}
            />
            {errors?.email && touchedFields.email && (
              <p>{errors.email.message}</p>
            )}
            <br />
            {errorMessage && (
              <Notification
                type={NotificationType.ERROR}
                header={errorMessage}
                showCloseIcon={false}
                fullWidth
              />
            )}
            {successMessage && (
              <Notification
                type={NotificationType.SUCCESS}
                header={successMessage}
                showCloseIcon={false}
                fullWidth
              />
            )}
            <br />
            <Button type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting ? 'Updating User...' : 'Update User'}
            </Button>
          </form>
        </div>
      </Dialog>
    </div>
  );
};

export default EditUserModal;
