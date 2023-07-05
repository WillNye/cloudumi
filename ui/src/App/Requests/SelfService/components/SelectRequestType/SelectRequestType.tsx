import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';

import styles from './SelectRequestType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { SELF_SERVICE_STEPS } from '../../constants';
import { useQuery } from '@tanstack/react-query';
import { getRequestType } from 'core/API/iambicRequest';
import { AxiosError } from 'axios';
import { getRequestTypeIcon } from './utils';
import NoResults from '../NoResults/NoResults';

const SelectRequestType = () => {
  const { selfServiceRequest } = useContext(SelfServiceContext).store;

  const {
    actions: { setCurrentStep, setSelectedRequestType }
  } = useContext(SelfServiceContext);

  const { data: requestTypes, isLoading } = useQuery({
    queryFn: getRequestType,
    queryKey: [
      'getRequestType',
      selfServiceRequest.provider,
      selfServiceRequest.identityType
    ],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
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
          {requestTypes?.data?.length ? (
            requestTypes.data.map(requestType => (
              <RequestCard
                key={requestType.id}
                title={requestType.name}
                icon={getRequestTypeIcon(requestType.name)}
                description={requestType.description}
                onClick={() => {
                  setCurrentStep(SELF_SERVICE_STEPS.SUGGESTED_CHANGE_TYPES);
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
