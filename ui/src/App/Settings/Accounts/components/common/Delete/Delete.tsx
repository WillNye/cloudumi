import { FC, Fragment, useCallback, useMemo, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import styles from './Delete.module.css';
import { DELETE_DATA_TYPE } from 'App/Settings/Accounts/constants';
import { deleteGroup, deleteUser } from 'core/API/settings';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useMutation } from '@tanstack/react-query';

interface DeleteProps {
  canEdit: boolean;
  dataType: DELETE_DATA_TYPE;
  dataId: string;
  title: string;
  refreshData: () => void;
}

type DeleteUserGroupParams = {
  [x: string]: string;
};

const Delete: FC<DeleteProps> = ({
  canEdit,
  dataType,
  dataId,
  title,
  refreshData
}) => {
  const [showDialog, setShowDialog] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const isUser = useMemo(() => dataType === DELETE_DATA_TYPE.USER, [dataType]);

  const deleteUserMutation = useMutation({
    mutationFn: (data: DeleteUserGroupParams) => deleteUser(data)
  });
  const deleteGroupMutation = useMutation({
    mutationFn: (data: DeleteUserGroupParams) => deleteGroup(data)
  });

  const handleOnSubmit = useCallback(async () => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsLoading(true);
    try {
      const deleteAction = isUser ? deleteUserMutation : deleteGroupMutation;
      const deleteKey = isUser ? 'email' : 'name';
      await deleteAction.mutateAsync({
        [deleteKey]: dataId
      });
      setSuccessMessage(`Successfully deleted ${dataType}: ${dataId}`);
      setIsLoading(false);
      setShowDialog(false);
      refreshData();
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || `An error occurred while deleting ${dataType}: ${dataId}`
      );
      setIsLoading(false);
    }
  }, [
    dataId,
    isUser,
    dataType,
    refreshData,
    deleteGroupMutation,
    deleteUserMutation
  ]);

  if (!canEdit) {
    return <Fragment />;
  }

  return (
    <div className={styles.container}>
      <div className={styles.btn} onClick={() => setShowDialog(true)}>
        <Icon name="delete" size="medium" />
      </div>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header={title}
        disablePadding
        size="small"
      >
        <div className={styles.content}>
          <div>
            {`Are you sure you want to delete this ${dataType}: `}{' '}
            <strong>{dataId}?</strong>
          </div>
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
          <div className={styles.deleteActions}>
            <Button
              className={styles.btn}
              color="error"
              onClick={handleOnSubmit}
              fullWidth
              disabled={isLoading}
            >
              {isLoading ? 'Deleting...' : 'Delete'}
            </Button>
            <Button
              color="secondary"
              variant="outline"
              onClick={() => setShowDialog(false)}
              fullWidth
            >
              Cancel
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default Delete;
