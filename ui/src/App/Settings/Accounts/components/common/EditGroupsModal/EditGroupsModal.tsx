import { FC, Fragment, useCallback, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { Button } from 'shared/elements/Button';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import { updateGroup } from 'core/API/settings';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Group } from '../../../types';
import styles from './EditGroupsModal.module.css';

type EditGroupsModalProps = {
  canEdit: boolean;
  group: Group;
};

const updatingGroupSchema = Yup.object().shape({
  name: Yup.string().required('Required'),
  description: Yup.string().required('Required')
});

const EditGroupsModal: FC<EditGroupsModalProps> = ({ canEdit, group }) => {
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
    resolver: yupResolver(updatingGroupSchema),
    defaultValues: {
      description: group.description,
      name: group.name
    }
  });

  const onSubmit = useCallback(
    async ({ name, description }) => {
      setErrorMessage(null);
      setSuccessMessage(null);
      try {
        await updateGroup({
          id: group.id,
          name,
          description
        });
        setSuccessMessage('Successfully updated group');
        // TODO refetch all groups
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while updating new group'
        );
      }
    },
    [group.id]
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
        header="Group Modal"
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
              {isSubmitting ? 'Updating Group...' : 'Update Group'}
            </Button>
          </form>
        </div>
      </Dialog>
    </div>
  );
};

export default EditGroupsModal;
