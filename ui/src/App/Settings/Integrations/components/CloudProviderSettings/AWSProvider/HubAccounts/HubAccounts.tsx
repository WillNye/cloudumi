import { Table } from 'shared/elements/Table';
import { HubAccountsColumns } from './constants';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { deleteHubAccount, getHubAccounts } from 'core/API/awsConfig';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { HubAccount } from './types';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import { HubAccountModal } from './HubAccountModal';
import styles from '../AWSProvider.module.css';
import DeleteModal from '../DeleteModal';

const HubAccounts = ({ aws }) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showDialog, setShowDialog] = useState(false);
  const [hubAccounts, setHubAccounts] = useState<HubAccount[]>([]);
  const [defaultData, setDefaultData] = useState<HubAccount | null>(null);

  useEffect(function onMount() {
    getAllHubAccounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getAllHubAccounts = useCallback(async () => {
    setErrorMessage(null);
    setIsLoading(true);
    try {
      const res = await getHubAccounts();
      const resData = res?.data?.data;
      setHubAccounts([resData]);
      setDefaultData(resData);
      setIsLoading(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting hub account'
      );
      setIsLoading(false);
    }
  }, []);

  const handleDeleteHubAccount = useCallback(
    async (awsOrganization: HubAccount) => {
      return deleteHubAccount(awsOrganization);
    },
    []
  );

  const tableRows = useMemo(() => {
    return hubAccounts.map(item => ({
      ...item,
      actions: (
        <div className={styles.tableActions}>
          <DeleteModal
            title="Delete Hub Account"
            warningMessage="Are you sure you want to delete this item? This action cannot be undone and all
             associated data will be permanently removed."
            refreshData={getAllHubAccounts}
            onDelete={handleDeleteHubAccount}
            data={item}
          />
        </div>
      )
    }));
  }, [hubAccounts, getAllHubAccounts, handleDeleteHubAccount]);

  return (
    <div className={styles.section}>
      <h3 className={styles.header}>Hub Account</h3>
      <div className={styles.content}>
        <div className={styles.headerActions}>
          <Button icon="refresh" onClick={getAllHubAccounts}></Button>
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
