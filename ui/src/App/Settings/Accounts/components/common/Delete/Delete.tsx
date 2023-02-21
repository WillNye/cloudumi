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

interface DeleteProps {
  canEdit: boolean;
  dataType: DELETE_DATA_TYPE;
  dataId: string;
}

const Delete: FC<DeleteProps> = ({ canEdit, dataType, dataId }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const isUser = useMemo(() => dataType === DELETE_DATA_TYPE.USER, [dataType]);

  const handleOnSubmit = useCallback(async () => {
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const deleteAction = isUser ? deleteUser : deleteGroup;
      const deleteKey = isUser ? 'email' : 'name';
      await deleteAction({
        [deleteKey]: dataId
      });
      setSuccessMessage(`Successfully deleted ${dataType}: ${dataId}`);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || `An error occurred while deleting ${dataType}: ${dataId}`
      );
    }
  }, [dataId, isUser, dataType]);

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
        header="Delete Modal"
        disablePadding
        size="small"
      >
        <div className={styles.content}>
          <div>{`Are you sure you want to delete this ${dataType}: ${dataId}?`}</div>
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
            <Button color="error" onClick={handleOnSubmit} fullWidth>
              Delete
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
