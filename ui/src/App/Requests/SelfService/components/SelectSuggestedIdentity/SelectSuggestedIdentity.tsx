import { useEffect, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectSuggestedIdentity.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getChangeRequestType } from 'core/API/iambicRequest';
import { ChangeType, Identity } from '../../types';
import { SELF_SERVICE_STEPS } from '../../constants';
import { Card } from 'shared/layout/Card';
import { Search } from 'shared/form/Search';
import { Button } from 'shared/elements/Button';
import { Link } from 'react-router-dom';

const TEST_IDENTITIES = [
  {
    id: '2080b8cf-af78-4356-bb8a-305ba329f70f',
    resource_id: 'poweruser',
    resource_type: 'IAM Role',
    template_type: 'NOQ::AWS::IAM::Role',
    provider: 'aws'
  },
  {
    id: 'fa0a38c7-0654-4ee1-9813-296a8f85addb',
    resource_id: 'NullRole',
    resource_type: 'IAM Role',
    template_type: 'NOQ::AWS::IAM::Role',
    provider: 'aws'
  },
  {
    id: 'b9e4fd21-bf7d-4225-ad40-897c8783e018',
    resource_id: 'IambicTestDeployUser',
    resource_type: 'IAM User',
    template_type: 'NOQ::AWS::IAM::User',
    provider: 'aws'
  },
  {
    id: '69d44d4d-72b8-486e-89ef-43999eadbe58',
    resource_id: 'AWSReadOnlyAccess',
    resource_type: 'Identity Center Permission Set',
    template_type: 'NOQ::AWS::IdentityCenter::PermissionSet',
    provider: 'aws'
  },
  {
    id: '421ab97f-d6ed-4678-ac98-eec3e81caebe',
    resource_id: 'adino',
    resource_type: 'IAM Managed Policy',
    template_type: 'NOQ::AWS::IAM::ManagedPolicy',
    provider: 'aws'
  },
  {
    id: '7d8785fe-1733-460f-a47f-8fbe794326b0',
    resource_id: 'ctaccess',
    resource_type: 'IAM Group',
    template_type: 'NOQ::AWS::IAM::Group',
    provider: 'aws'
  },
  {
    id: '2a582644-4f16-4d72-a660-5834f99d4750',
    resource_id: 'NoqSaasRoleLocalDev',
    resource_type: 'IAM Role',
    template_type: 'NOQ::AWS::IAM::Role',
    provider: 'aws'
  }
];

const SelectSuggestedIdentity = () => {
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
        <div className={styles.cardContainer}>
          {TEST_IDENTITIES?.map(identity => (
            <Card
              variant="outlined"
              color={
                selectedCard === identity.resource_id ? 'primary' : 'secondary'
              }
              className={`${styles.card}`}
              key={identity.id}
              onClick={() => handleCardClick(identity)}
              clickable
              header={identity.resource_id}
            >
              <p>{identity?.resource_type}</p>
            </Card>
          ))}
        </div>
      </div>
    </Segment>
  );
};

export default SelectSuggestedIdentity;
