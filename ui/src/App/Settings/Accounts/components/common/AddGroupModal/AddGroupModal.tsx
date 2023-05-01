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
import { createGroup } from 'core/API/settings';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useMutation } from '@tanstack/react-query';
import styles from './AddGroupModal.module.css';

type CreateGroupParams = { name: string; description: string };

const addGroupSchema = Yup.object().shape({
  name: Yup.string().required('Required'),
  description: Yup.string().required('Required')
});

export const AddGroupModal = ({ refreshData }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const createGroupMutation = useMutation({
    mutationFn: (data: CreateGroupParams) => createGroup(data)
  });

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, isValid, errors, touchedFields }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(addGroupSchema),
    defaultValues: {
      description: '',
      name: ''
    }
  });

  const onSubmit = useCallback(
    async ({ name, description }) => {
      setErrorMessage(null);
      setSuccessMessage(null);
      try {
        await createGroupMutation.mutateAsync({
          name,
          description
        });
        setSuccessMessage('Successfully added new group');
        refreshData();
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(errorMsg || 'An error occurred while adding new group');
      }
    },
    [refreshData, createGroupMutation]
  );

  return (
    <div className={styles.container}>
      <Button onClick={() => setShowDialog(true)}>Create Group</Button>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        disablePadding
        header="Create Group"
        size="medium"
      >
        <div className={styles.content}>
          <form onSubmit={handleSubmit(onSubmit)}>
            <Block disableLabelPadding label="Name" required></Block>
            <Input
              fullWidth
              placeholder="name"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('name')}
            />
            {errors?.name && touchedFields.name && <p>{errors.name.message}</p>}
            <br />
            <Block disableLabelPadding label="Description" required></Block>
            <Input
              fullWidth
              placeholder="description"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('description')}
            />
            {errors?.description && touchedFields.description && (
              <p>{errors.description.message}</p>
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
              {isSubmitting ? 'Adding Group...' : 'Add Group'}
            </Button>
          </form>
        </div>
      </Dialog>
    </div>
  );
};

export default AddGroupModal;
