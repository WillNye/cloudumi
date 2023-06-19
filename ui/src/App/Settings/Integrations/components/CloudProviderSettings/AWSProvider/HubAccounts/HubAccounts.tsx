import { Table } from 'shared/elements/Table';
import { HubAccountsColumns } from './constants';
import { deleteHubAccount } from 'core/API/awsConfig';
import { useMemo, useState } from 'react';
import { HubAccount } from './types';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import { HubAccountModal } from './HubAccountModal';
import DeleteModal from '../DeleteModal';
import { useMutation } from '@tanstack/react-query';

import styles from '../AWSProvider.module.css';

const HubAccounts = ({ aws, isLoading, refetch, hubAccounts }) => {
  const [showDialog, setShowDialog] = useState(false);

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
          defaultValues={hubAccounts?.length ? hubAccounts[0] : null}
          aws={aws}
        />
      </Dialog>
    </div>
  );
};

export default HubAccounts;
