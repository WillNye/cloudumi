import HubAccounts from './HubAccounts';
import SpokeAccounts from './SpokeAccounts';
import AWSOrganizations from './AWSOrganizations';
import styles from './AWSProvider.module.css';
import { Segment } from 'shared/layout/Segment';
import { useState } from 'react';
import { awsIntegrations, getHubAccounts } from 'core/API/awsConfig';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { useQuery } from '@tanstack/react-query';
import { HubAccount } from './HubAccounts/types';

const AWSProvider = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [hubAccounts, setHubAccounts] = useState<HubAccount[]>([]);

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

  const { refetch: refetchHubAccounts, isLoading: isHubLoading } = useQuery({
    queryFn: getHubAccounts,
    queryKey: ['getHubAccounts'],
    onSuccess: ({ data }) => {
      if (data?.account_id) {
        setHubAccounts([data]);
      }
    },
    onError: (err: AxiosError) => {
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting hub account'
      );
    }
  });

  return (
    <div className={styles.aws}>
      <Segment isLoading={isLoading} disablePadding>
        <HubAccounts
          aws={data}
          isLoading={isHubLoading}
          refetch={refetchHubAccounts}
          hubAccounts={hubAccounts}
        />
        <SpokeAccounts aws={data} hubAccounts={hubAccounts} />
        <AWSOrganizations />
      </Segment>
    </div>
  );
};

export default AWSProvider;
