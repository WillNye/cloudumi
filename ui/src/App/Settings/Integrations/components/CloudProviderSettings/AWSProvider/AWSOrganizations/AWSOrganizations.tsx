import { Table } from 'shared/elements/Table';
import { AWSOrganizationCoulumns } from './constants';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { AWSOrganization } from './types';
import { deleteAWSOrganization, getAWSOrganizations } from 'core/API/awsConfig';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import { AWSOrganizationModal } from './AWSOrganizationModal';
import styles from '../AWSProvider.module.css';
import DeleteModal from '../DeleteModal';

const AWSOrganizations = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showDialog, setShowDialog] = useState(false);
  const [awsOrganizations, setAWSOrganizations] = useState<AWSOrganization[]>(
    []
  );
  const [defaultData, setDefaultData] = useState<AWSOrganization>(null);

  useEffect(function onMount() {
    getAllAWSOrganizations();
  }, []);

  const getAllAWSOrganizations = useCallback(async () => {
    setErrorMessage(null);
    setIsLoading(true);
    try {
      const res = await getAWSOrganizations();
      const resData = res?.data?.data;
      setAWSOrganizations(resData ?? []);
      setIsLoading(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting AWS organizations'
      );
      setIsLoading(false);
    }
  }, []);

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
            warningMessage="Are you sure you want to delete this item? This action cannot be undone and all associated data will be permanently removed."
            refreshData={getAllAWSOrganizations}
            onDelete={handleDeleteOrganizationAccount}
            data={item}
          />
        </div>
      )
    }));
  }, [
    awsOrganizations,
    getAllAWSOrganizations,
    handleDeleteOrganizationAccount,
    openEditOrganizationModal
  ]);

  return (
    <div className={styles.section}>
      <h3 className={styles.header}>AWS Organizations</h3>
      <div className={styles.content}>
        <div className={styles.headerActions}>
          <Button icon="refresh" onClick={getAllAWSOrganizations}></Button>
          <Button size="small" onClick={openNewOrganizationModal}>
            New
          </Button>
        </div>
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
        <AWSOrganizationModal
          onClose={() => setShowDialog(false)}
          defaultValues={defaultData}
        />
      </Dialog>
    </div>
  );
};

export default AWSOrganizations;
