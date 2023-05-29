import { useCallback, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';

import { Block } from 'shared/layout/Block';
import { Input } from 'shared/form/Input';
import { Button } from 'shared/elements/Button';

import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { extractErrorMessage } from 'core/API/utils';
import { AxiosError } from 'axios';
import { createUser } from 'core/API/settings';
import { Notification, NotificationType } from 'shared/elements/Notification';
import styles from './InviteUserModal.module.css';
import { useMutation } from '@tanstack/react-query';
import { LineBreak } from 'shared/elements/LineBreak';

type CreateUserParams = {
  email: string;
  password: string;
};

const addUserSchema = Yup.object().shape({
  email: Yup.string().email().required('Required')
});

const InviteUserModal = ({ refreshData }) => {
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
    resolver: yupResolver(addUserSchema),
    defaultValues: {
      email: '',
      password: ''
    }
  });

  const { mutateAsync: createUserMutation } = useMutation({
    mutationFn: (data: CreateUserParams) => createUser(data)
  });

  const onSubmit = useCallback(
    async ({ email, password }) => {
      setErrorMessage(null);
      setSuccessMessage(null);
      try {
        await createUserMutation({
          email,
          password
        });
        setSuccessMessage('Successfully invited new user');
        refreshData();
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(errorMsg || 'An error occurred while adding new user');
      }
    },
    [refreshData, createUserMutation]
  );

  return (
    <div className={styles.container}>
      <Button onClick={() => setShowDialog(true)}>Invite User</Button>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        disablePadding
        header="Invite Team Member"
        size="medium"
      >
        <div className={styles.content}>
          <form onSubmit={handleSubmit(onSubmit)}>
            {/* <div className={styles.userNames}>
                <div>
              <Block disableLabelPadding label="First Name"></Block>
              <Input fullWidth name="first_name" />
              </div>
              <div>

              <Block disableLabelPadding label="Last Name"></Block>
              <Input fullWidth name="last_name" />
              </div>
            </div> */}
            <Block disableLabelPadding label="Email" required></Block>
            <Input
              fullWidth
              name="email"
              placeholder="Email"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('email')}
            />
            {errors?.email && touchedFields.email && (
              <p>{errors.email.message}</p>
            )}
            <LineBreak />
            <Block disableLabelPadding label="Password"></Block>
            <Input
              fullWidth
              name="Password"
              type="password"
              placeholder="Password"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('password')}
            />
            {/* TODO: Password validatio required */}
            {errors?.password && touchedFields.password && (
              <p>{errors.password.message}</p>
            )}
            <LineBreak />
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
            <LineBreak />
            <Button type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting ? 'Sending Invite...' : 'Send Invite'}
            </Button>
          </form>
        </div>
      </Dialog>
    </div>
  );
};

export default InviteUserModal;
