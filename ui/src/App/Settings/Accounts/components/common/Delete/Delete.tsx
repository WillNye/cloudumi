import { FC, Fragment, useCallback, useMemo, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import styles from './Delete.module.css';
import { DELETE_DATA_TYPE } from 'App/Settings/Accounts/constants';
import { deleteGroup, deleteUser } from 'core/API/settings';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { LineBreak } from 'shared/elements/LineBreak';
import { toast } from 'react-toastify';
import { Divider } from 'shared/elements/Divider';

interface DeleteProps {
  canEdit?: boolean;
  dataType: DELETE_DATA_TYPE;
  dataId: string;
  title: string;
}

type DeleteUserGroupParams = {
  [x: string]: string;
};

const Delete: FC<DeleteProps> = ({ canEdit, dataType, dataId, title }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const queryClient = useQueryClient();

  const isUser = useMemo(() => dataType === DELETE_DATA_TYPE.USER, [dataType]);

  const { mutateAsync: deleteUserMutation } = useMutation({
    mutationFn: (data: DeleteUserGroupParams) => deleteUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`allUsers`] });
    }
  });
  const { mutateAsync: deleteGroupMutation } = useMutation({
    mutationFn: (data: DeleteUserGroupParams) => deleteGroup(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`allGroups`] });
    }
  });

  const handleOnSubmit = useCallback(async () => {
    setIsLoading(true);
    try {
      const deleteAction = isUser ? deleteUserMutation : deleteGroupMutation;
      const deleteKey = isUser ? 'email' : 'name';
      await deleteAction({
        [deleteKey]: dataId
      });
      toast.success(`Successfully deleted ${dataType}: ${dataId}`);
      setIsLoading(false);
      setShowDialog(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      toast.error(
        errorMsg || `An error occurred while deleting ${dataType}: ${dataId}`
      );
      setIsLoading(false);
    }
  }, [dataId, isUser, dataType, deleteGroupMutation, deleteUserMutation]);

  if (!(canEdit ?? true)) {
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
          <LineBreak size="large" />
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
            <Divider orientation="vertical" />
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
