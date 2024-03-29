import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { deleteAWSOrganization, getAWSOrganizations } from 'core/API/awsConfig';
import { extractErrorMessage } from 'core/API/utils';
import { useCallback, useMemo, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Table } from 'shared/elements/Table';
import { Dialog } from 'shared/layers/Dialog';
import styles from '../AWSProvider.module.css';
import DeleteModal from '../DeleteModal';
import { AWSOrganizationModal } from './AWSOrganizationModal';
import {
  AWSOrganizationCoulumns,
  AWS_ORGANIZATION_DELETE_MESSAGE
} from './constants';
import { AWSOrganization } from './types';
import RefreshAccountsModal from '../RefreshAccountsModal/RefreshAccountsModal';

const AWSOrganizations = ({ forceOnboardAccounts }) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [awsOrganizations, setAWSOrganizations] = useState<AWSOrganization[]>(
    []
  );
  const [defaultData, setDefaultData] = useState<AWSOrganization>(null);
  const [showRefreshModal, setShowRefreshModal] = useState(false);

  const { refetch, isLoading } = useQuery({
    queryFn: getAWSOrganizations,
    queryKey: ['getAWSOrganizations'],
    onSuccess: data => {
      setAWSOrganizations(data?.data ?? []);
    },
    onError: (err: AxiosError) => {
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting AWS organizations'
      );
    }
  });

  const handleDeleteOrganizationAccount = useCallback(
    async (awsOrganization: AWSOrganization) => {
      return deleteAWSOrganization(awsOrganization);
    },
    []
  );

  const openEditOrganizationModal = useCallback((data: AWSOrganization) => {
    setDefaultData(data);
    setShowDialog(true);
  }, []);

  const openNewOrganizationModal = useCallback(() => {
    setDefaultData(null);
    setShowDialog(true);
  }, []);

  const tableRows = useMemo(() => {
    return awsOrganizations.map(item => ({
      ...item,
      actions: (
        <div className={styles.tableActions}>
          <Button
            color="secondary"
            variant="outline"
            size="small"
            onClick={() => openEditOrganizationModal(item)}
          >
            Edit
          </Button>
          <DeleteModal
            title="Delete Aws Organization"
            warningMessage={AWS_ORGANIZATION_DELETE_MESSAGE}
            refreshData={refetch}
            onDelete={handleDeleteOrganizationAccount}
            data={item}
          />
        </div>
      )
    }));
  }, [
    awsOrganizations,
    refetch,
    handleDeleteOrganizationAccount,
    openEditOrganizationModal
  ]);

  const accountsNotOnboarded = useMemo(() => {
    return awsOrganizations.map(
      item => item.accounts_excluded_from_automatic_onboard
    );
  }, [awsOrganizations]);

  return (
    <div className={styles.section}>
      <h3 className={styles.header}>AWS Organizations</h3>
      <div className={styles.content}>
        <div className={styles.headerActions}>
          {accountsNotOnboarded && (
            <Button
              style={{ marginRight: 'auto' }}
              icon="refresh"
              onClick={() => {
                forceOnboardAccounts();
                setShowRefreshModal(true);
              }}
            >
              Refresh Accounts from AWS Organizations
            </Button>
          )}
          <Button icon="refresh" onClick={() => refetch()}></Button>
          <Button size="small" onClick={openNewOrganizationModal}>
            New
          </Button>
        </div>
        <RefreshAccountsModal
          show={showRefreshModal}
          onClose={() => setShowRefreshModal(false)}
        />
        <Table
          columns={AWSOrganizationCoulumns}
          data={tableRows}
          isLoading={isLoading}
          border="row"
        />
      </div>
      <Dialog
        header="AWS Organizations"
        size="medium"
        setShowDialog={setShowDialog}
        showDialog={showDialog}
      >
        <AWSOrganizationModal defaultValues={defaultData} />
      </Dialog>
    </div>
  );
};

export default AWSOrganizations;
