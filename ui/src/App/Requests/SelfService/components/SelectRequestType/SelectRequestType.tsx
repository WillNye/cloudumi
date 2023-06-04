import { useEffect, useState } from 'react';
import axios from 'core/Axios/Axios';
import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';
import identityIcon from 'assets/vendor/identity.svg';
import accessIcon from 'assets/vendor/access.svg';
import permissionsIcon from 'assets/vendor/permissions.svg';

import styles from './SelectRequestType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext, { RequestType } from '../../SelfServiceContext';
import { SELF_SERICE_STEPS } from '../../constants';
import { Button } from 'shared/elements/Button';

interface ApiResponse {
  status_code: number;
  data: RequestType[];
}

const SelectRequestType = () => {
  const [requestTypes, setRequestTypes] = useState<RequestType[]>([]);
  const { selectedProvider } = useContext(SelfServiceContext).store;

  const {
    actions: { setCurrentStep, setSelectedRequestType, goBack }
  } = useContext(SelfServiceContext);

  useEffect(() => {
    if (selectedProvider) {
      const fetchData = async () => {
        const result = await axios.get<ApiResponse>(
          `/api/v4/self-service/request-types?provider=${selectedProvider}`
        );
        setRequestTypes(result.data.data);
      };

      fetchData();
    }
  }, [selectedProvider]);

  return (
    <Segment>
      <div className={styles.container}>
        <h3>Request Type</h3>
        <LineBreak />
        <p className={styles.subText}>What would you like to do?</p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          {requestTypes.map(requestType => (
            <RequestCard
              key={requestType.id}
              title={requestType.name}
              icon={identityIcon} // replace with appropriate icon
              description={requestType.description}
              onClick={() => {
                setCurrentStep(SELF_SERICE_STEPS.CHANGE_TYPE);
                setSelectedRequestType(requestType);
              }}
            />
          ))}
        </div>
        <Button onClick={goBack}>Back</Button>
      </div>
    </Segment>
  );
};

export default SelectRequestType;
