import { useEffect, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './ExpressChangeDetails.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getChangeRequestType } from 'core/API/iambicRequest';
import { ChangeType, Identity } from '../../../types';
import { SELF_SERVICE_STEPS } from '../../../constants';
import { Card } from 'shared/layout/Card';
import { Search } from 'shared/form/Search';
import { Button } from 'shared/elements/Button';
import { Link } from 'react-router-dom';

const ExpressChangeDetails = () => {
  const {
    actions: { setCurrentStep, setSelectedIdentity, setSelectedIdentityType }
  } = useContext(SelfServiceContext);
  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

  const selectedRequestType = useMemo(
    () => selfServiceRequest.requestType,
    [selfServiceRequest]
  );

  const [suggestedIdentity, setSuggestedIdentities] = useState<Identity[]>([]);

  const [selectedCard, setSelectedCard] = useState(null);

  const handleCardClick = identity => {
    if (selectedCard === identity.resource_id) {
      setSelectedIdentity(null);
      setSelectedCard(null);
      setSelectedIdentityType(null);
    } else {
      setSelectedIdentityType(identity.template_type);
      setSelectedIdentity(identity);
      setSelectedCard(identity.resource_id);
    }
  };

  // Temp remove:
  const isLoading = false;

  // const { data: identities, isLoading } = useQuery({
  //   queryFn: getIdentities,
  //   queryKey: [
  //     'getIdentities',
  //     'true'
  //   ],
  //   onError: (error: AxiosError) => {
  //     // const errorRes = error?.response;
  //     // const errorMsg = extractErrorMessage(errorRes?.data);
  //     // setErrorMessage(errorMsg || 'An error occurred fetching resource');
  //   }
  // });

  // useEffect(() => {
  //   if (changeTypes) {
  //     console.log('HERE', changeTypes);
  //     setSuggestedChangeTypes(changeTypes?.data.concat(SUGGESTED_CHANGES));
  //   }
  // }, [changeTypes]);

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Which Cloud Identity would you like to add this to?</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please select one of the suggested identities below
        </p>
        <LineBreak />
        <div className={styles.search}>
          Can&apos;t find what you&apos;re looking for?{' '}
          <a
            href="#"
            onClick={e => {
              e.preventDefault();
              setCurrentStep(SELF_SERVICE_STEPS.SELECT_IDENTITY);
            }}
          >
            click here
          </a>{' '}
          to customize your request
        </div>
        <LineBreak />
        <div className={styles.cardContainer}>{/* TODO */}</div>
      </div>
    </Segment>
  );
};

export default ExpressChangeDetails;
