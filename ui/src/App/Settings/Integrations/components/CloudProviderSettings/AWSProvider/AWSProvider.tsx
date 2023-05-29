import HubAccounts from './HubAccounts';
import SpokeAccounts from './SpokeAccounts';
import AWSOrganizations from './AWSOrganizations';
import styles from './AWSProvider.module.css';
import { Segment } from 'shared/layout/Segment';
import { useState } from 'react';
import { awsIntegrations } from 'core/API/awsConfig';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { useQuery } from '@tanstack/react-query';

const AWSProvider = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { isLoading, data } = useQuery({
    queryFn: awsIntegrations,
    queryKey: ['awsIntegrations'],
    onSuccess: () => {
      setErrorMessage(null);
    },
    onError: (err: AxiosError) => {
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting aws integrations'
      );
    }
  });

  return (
    <div className={styles.aws}>
      <Segment isLoading={isLoading} disablePadding>
        <HubAccounts aws={data} />
        <SpokeAccounts aws={data} />
        <AWSOrganizations />
      </Segment>
    </div>
  );
};

export default AWSProvider;
