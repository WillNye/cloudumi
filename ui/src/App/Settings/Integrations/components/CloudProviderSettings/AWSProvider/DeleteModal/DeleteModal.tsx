import { FC, Fragment, useCallback, useState } from 'react';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import styles from './DeleteModal.module.css';
import { AxiosError, AxiosResponse } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Notification, NotificationType } from 'shared/elements/Notification';

interface DeleteProps {
  showDeleteButton?: boolean;
  warningMessage: string;
  title: string;
  data: any;
  refreshData: () => void;
  onDelete: (data: any) => Promise<AxiosResponse<any, any>>;
}

const Delete: FC<DeleteProps> = ({
  showDeleteButton = true,
  warningMessage,
  title,
  onDelete,
  refreshData,
  data
}) => {
  const [showDialog, setShowDialog] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleOnSubmit = useCallback(async () => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsLoading(true);
    try {
      await onDelete(data);
      setSuccessMessage(`Successfully deleted Item`);
      refreshData();
      setIsLoading(false);
      setShowDialog(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(errorMsg || `An error occurred while deleting Item}`);
      setIsLoading(false);
    }
  }, [onDelete, refreshData, data]);

  if (!showDeleteButton) {
    return <Fragment />;
  }

  return (
    <>
      <Button
        color="secondary"
        variant="outline"
        size="small"
        onClick={() => setShowDialog(true)}
      >
        Remove
      </Button>
      <div className={styles.container}>
        <Dialog
          showDialog={showDialog}
          setShowDialog={setShowDialog}
          header={title}
          disablePadding
          size="medium"
        >
          <div className={styles.content}>
            <div>{warningMessage}</div>
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
    </>
  );
};

export default Delete;
