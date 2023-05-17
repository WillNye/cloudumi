import { Table } from 'shared/elements/Table';
import { HubAccountsColumns } from './constants';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { deleteHubAccount, getHubAccounts } from 'core/API/awsConfig';
import { useMemo, useState } from 'react';
import { HubAccount } from './types';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import { HubAccountModal } from './HubAccountModal';
import DeleteModal from '../DeleteModal';
import { useMutation, useQuery } from '@tanstack/react-query';

import styles from '../AWSProvider.module.css';

const HubAccounts = ({ aws }) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [hubAccounts, setHubAccounts] = useState<HubAccount[]>([]);
  const [defaultData, setDefaultData] = useState<HubAccount | null>(null);

  const { refetch, isLoading } = useQuery({
    queryFn: getHubAccounts,
    queryKey: ['getHubAccounts'],
    onSuccess: ({ data }) => {
      setHubAccounts([data]);
      setDefaultData(data);
    },
    onError: (err: AxiosError) => {
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting hub account'
      );
    }
  });

  const { mutateAsync: deleteHubAccountMutation } = useMutation({
    mutationFn: (awsOrganization: HubAccount) =>
      deleteHubAccount(awsOrganization),
    mutationKey: ['deleteHubAccount']
  });

  const tableRows = useMemo(() => {
    return hubAccounts.map(item => ({
      ...item,
      actions: (
        <div className={styles.tableActions}>
          <DeleteModal
            title="Delete Hub Account"
            warningMessage="Are you sure you want to delete this item? This action cannot be undone and all
             associated data will be permanently removed."
            refreshData={refetch}
            onDelete={deleteHubAccountMutation}
            data={item}
          />
        </div>
      )
    }));
  }, [hubAccounts, refetch, deleteHubAccountMutation]);

  return (
    <div className={styles.section}>
      <h3 className={styles.header}>Hub Account</h3>
      <div className={styles.content}>
        <div className={styles.headerActions}>
          <Button icon="refresh" onClick={() => refetch()}></Button>
          {!tableRows.length && (
            <Button size="small" onClick={() => setShowDialog(true)}>
              New
            </Button>
          )}
        </div>
        <Table
          columns={HubAccountsColumns}
          data={tableRows}
          isLoading={isLoading}
          border="row"
        />
      </div>
      <Dialog
        header="Add Hub Account"
        size="medium"
        setShowDialog={setShowDialog}
        showDialog={showDialog}
      >
        <HubAccountModal
          onClose={() => setShowDialog(false)}
          defaultValues={defaultData}
          aws={aws}
        />
      </Dialog>
    </div>
  );
};

export default HubAccounts;
