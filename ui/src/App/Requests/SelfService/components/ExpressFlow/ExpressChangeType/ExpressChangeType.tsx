import { useEffect, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './ExpressChangeType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getChangeRequestType } from 'core/API/iambicRequest';
import { ChangeType } from '../../../types';
import { SELF_SERVICE_STEPS } from '../../../constants';
import { Card } from 'shared/layout/Card';

const ExpressChangeType = () => {
  const [, setSelectedChangeType] = useState<ChangeType | null>(null);
  const {
    actions: { setCurrentStep, addChange, resetChanges },
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const [selectedCard, setSelectedCard] = useState(null);

  const selectedRequestType = useMemo(
    () => selfServiceRequest.requestType,
    [selfServiceRequest]
  );

  const [suggestedChangeTypes, setSuggestedChangeTypes] = useState<
    ChangeType[]
  >([]);

  const { data: changeTypes, isLoading } = useQuery({
    queryFn: getChangeRequestType,
    queryKey: [
      'getChangeRequestType',
      selectedRequestType?.id,
      'iambic_templates_specified',
      'true'
    ],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  const handleCardClick = changeType => {
    if (selectedCard?.id === changeType?.id) {
      setSelectedChangeType(null);
      setSelectedCard(null);
      resetChanges();
    } else {
      setSelectedChangeType;
      setSelectedCard(changeType);
      // TODO: We have a changeType that could be incomplete
      // We need to call addChange but may need to ask the user for
      // more info
    }
  };

  useEffect(() => {
    if (changeTypes) {
      console.log('HERE', changeTypes);
      setSuggestedChangeTypes(changeTypes?.data);
    }
  }, [changeTypes]);

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>What Permissions would you like?</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please select from the provided template suggestions
        </p>
        <LineBreak />
        <div className={styles.search}>
          Can&apos;t find what you&apos;re looking for?{' '}
          <a
            href="#"
            onClick={e => {
              e.preventDefault();
              setCurrentStep(SELF_SERVICE_STEPS.EXPRESS_CHANGE_DETAILS);
            }}
          >
            click here
          </a>{' '}
          to customize your request
        </div>
        <LineBreak />
        <div className={styles.cardContainer}>
          {suggestedChangeTypes.map(changeType => (
            <Card
              variant="outlined"
              color={
                selectedCard?.id === changeType?.id ? 'primary' : 'secondary'
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
