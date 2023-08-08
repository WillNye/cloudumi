import { useCallback, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './ExpressChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getExpressAccessRequests } from 'core/API/iambicRequest';
import { REQUEST_FLOW_MODE, SELF_SERVICE_STEPS } from '../../../constants';
import { Card } from 'shared/layout/Card';

const ExpressChangeType = () => {
  const {
    actions: { setCurrentStep, addChangeType, resetChanges, setCurrentMode },
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const [selectedCard, setSelectedCard] = useState(null);

  const { data: changeTypes, isLoading } = useQuery({
    queryFn: getExpressAccessRequests,
    queryKey: ['getExpressAccessRequests', selfServiceRequest.provider],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  const handleCardClick = useCallback(
    changeType => {
      if (selectedCard?.id === changeType?.id) {
        addChangeType(null);
        setSelectedCard(null);
        resetChanges();
      } else {
        addChangeType(changeType);
        setSelectedCard(changeType);
        // TODO: We have a changeType that could be incomplete
        // We need to call addChange but may need to ask the user for
        // more info
      }
    },
    [resetChanges, selectedCard?.id, addChangeType]
  );

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Request Help Wizard</h3>
        <LineBreak size="small" />
        <p className={styles.subText}>What do you need to access?</p>
        <LineBreak />
        <div className={styles.search}>
          Can&apos;t find what you&apos;re looking for?{' '}
          <a
            href="#"
            onClick={e => {
              e.preventDefault();
              setCurrentStep(SELF_SERVICE_STEPS.SELECT_IDENTITY);
              setCurrentMode(REQUEST_FLOW_MODE.ADVANCED_MODE);
            }}
          >
            click here
          </a>{' '}
          to customize your request
        </div>
        <LineBreak />
        <div className={styles.cardContainer}>
          {changeTypes?.data.map(changeType => (
            <Card
              variant="outlined"
              color={
                selectedCard?.id === changeType?.id ? 'primary' : 'default'
              }
              className={styles.card}
              key={changeType.id}
              onClick={() => handleCardClick(changeType)}
              clickable
              header={changeType.name}
            >
              <p>{changeType.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </Segment>
  );
};

export default ExpressChangeType;
