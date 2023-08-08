import { Segment } from 'shared/layout/Segment';
import RequestCard from '../common/RequestCard';

import styles from './SelectRequestType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { getRequestType } from 'core/API/iambicRequest';
import { AxiosError } from 'axios';
import { getRequestTypeIcon } from './utils';
import NoResults from '../common/NoResults';
import { REQUEST_FLOW_MODE } from '../../constants';

const SelectRequestType = () => {
  const { selfServiceRequest } = useContext(SelfServiceContext).store;

  const {
    actions: { setSelectedRequestType, handleNext, setCurrentMode }
  } = useContext(SelfServiceContext);

  const { data: requestTypes, isLoading } = useQuery({
    queryFn: getRequestType,
    queryKey: ['getRequestType', selfServiceRequest.provider],
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
                  const mode = requestType.express_request_support
                    ? REQUEST_FLOW_MODE.EXPRESS_MODE
                    : REQUEST_FLOW_MODE.ADVANCED_MODE;
                  setSelectedRequestType(requestType);
                  handleNext(mode);
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
