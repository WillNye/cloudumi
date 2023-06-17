import { Table } from 'shared/elements/Table';
import { SpokeAccountsColumns } from './constants';
import { Button } from 'shared/elements/Button';
import { useCallback, useMemo, useState } from 'react';
import { deleteSpokeAccount, getSpokeAccounts } from 'core/API/awsConfig';
import { SpokeAccount } from './types';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Dialog } from 'shared/layers/Dialog';
import { SpokeAccountModal } from './SpokeAccountModal';
import styles from '../AWSProvider.module.css';
import DeleteModal from '../DeleteModal';
import { useMutation, useQuery } from '@tanstack/react-query';

const SpokeAccounts = ({ aws, hubAccounts }) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [spokeAccounts, setSpokeAccounts] = useState<SpokeAccount[]>([]);
  const [showDialog, setShowDialog] = useState(false);
  const [defaultData, setDefaultData] = useState<SpokeAccount>(null);

  const { isLoading, refetch } = useQuery({
    queryFn: getSpokeAccounts,
    queryKey: ['getSpokeAccounts'],
    onSuccess: ({ data }) => {
      setSpokeAccounts(data);
    },
    onError: (err: AxiosError) => {
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting spoke accounts'
      );
    }
  });

  const { mutateAsync: deleteSpokeAccountMutation } = useMutation({
    mutationFn: (spokeAccount: SpokeAccount) =>
      deleteSpokeAccount(spokeAccount),
    mutationKey: ['deleteSpokeAccount']
  });

  const openEditSpokeModal = useCallback((data: SpokeAccount) => {
    setDefaultData(data);
    setShowDialog(true);
  }, []);

  const openNewSpokeModal = useCallback(() => {
    setDefaultData(null);
    setShowDialog(true);
  }, []);

  const tableRows = useMemo(() => {
    return spokeAccounts.map(item => ({
      ...item,
      actions: (
        <div className={styles.tableActions}>
          <Button
            color="secondary"
            variant="outline"
            size="small"
            onClick={() => openEditSpokeModal(item)}
          >
            Edit
          </Button>
          <DeleteModal
            title="Delete Spoke Account"
            warningMessage="Are you sure you want to delete this item? This action cannot be undone and all
             associated data will be permanently removed."
            refreshData={refetch}
            onDelete={deleteSpokeAccountMutation}
            data={item}
          />
        </div>
      )
    }));
  }, [spokeAccounts, refetch, deleteSpokeAccountMutation, openEditSpokeModal]);

  return (
    <div className={styles.section}>
      <h3 className={styles.header}>Spoke Accounts</h3>
      <div className={styles.content}>
        <div className={styles.headerActions}>
          <Button icon="refresh" onClick={() => refetch()}></Button>
          <Button
            size="small"
            onClick={openNewSpokeModal}
            disabled={!hubAccounts?.length}
          >
            New
          </Button>
        </div>
        <Table
          columns={SpokeAccountsColumns}
          data={tableRows}
          isLoading={isLoading}
          border="row"
        />
      </div>
      <Dialog
        header="Add Spoke Account"
        size="medium"
        setShowDialog={setShowDialog}
        showDialog={showDialog}
      >
        <SpokeAccountModal defaultValues={defaultData} aws={aws} />
      </Dialog>
    </div>
  );
};

export default SpokeAccounts;
