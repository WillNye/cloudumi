import { useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';

import styles from './SelectRequestType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { SELF_SERICE_STEPS } from '../../constants';
import { RequestType } from '../../types';
import { useQuery } from '@tanstack/react-query';
import { getRequestType } from 'core/API/iambicRequest';
import { AxiosError } from 'axios';
import { getRequestTypeIcon } from './utils';
import NoResults from '../NoResults/NoResults';

const SelectRequestType = () => {
  const [requestTypes, setRequestTypes] = useState<RequestType[]>([]);
  const { selectedProvider } = useContext(SelfServiceContext).store;

  const {
    actions: { setCurrentStep, setSelectedRequestType }
  } = useContext(SelfServiceContext);

  const { data, isLoading } = useQuery({
    queryFn: getRequestType,
    queryKey: ['getRequestType', selectedProvider],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    },
    onSuccess: ({ data }) => {
      console.log(data, '--------');
      setRequestTypes(data);
    }
  });

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Request Type</h3>
        <LineBreak />
        <p className={styles.subText}>What would you like to do?</p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          {requestTypes?.length ? (
            requestTypes.map(requestType => (
              <RequestCard
                key={requestType.id}
                title={requestType.name}
                icon={getRequestTypeIcon(requestType.name)}
                description={requestType.description}
                onClick={() => {
                  setCurrentStep(SELF_SERICE_STEPS.CHANGE_TYPE);
                  setSelectedRequestType(requestType);
                }}
              />
            ))
          ) : (
            <NoResults />
          )}
        </div>
      </div>
    </Segment>
  );
};

export default SelectRequestType;
