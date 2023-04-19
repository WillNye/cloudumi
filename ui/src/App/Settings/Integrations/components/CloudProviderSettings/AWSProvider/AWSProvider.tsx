import { Link } from 'react-router-dom';
import HubAccounts from './HubAccounts';
import SpokeAccounts from './SpokeAccounts';
import AWSOrganizations from './AWSOrganizations';
import styles from './AWSProvider.module.css';
import { Segment } from 'shared/layout/Segment';
import { useCallback, useEffect, useState } from 'react';
import { awsIntegrations } from 'core/API/awsConfig';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';

const AWSProvider = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [awsData, setAWSData] = useState(null);

  useEffect(function onMount() {
    getAWSIntegrations();
  }, []);

  const getAWSIntegrations = useCallback(async () => {
    setErrorMessage(null);
    setIsLoading(true);
    try {
      const res = await awsIntegrations();
      const resData = res?.data;
      setIsLoading(false);
      setAWSData(resData);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while getting aws integrations'
      );
      setIsLoading(false);
    }
  }, []);

  return (
    <div className={styles.aws}>
      <Segment isLoading={isLoading} disablePadding>
        <HubAccounts aws={awsData} />
        <SpokeAccounts aws={awsData} />
        <AWSOrganizations />
      </Segment>
    </div>
  );
};

export default AWSProvider;
