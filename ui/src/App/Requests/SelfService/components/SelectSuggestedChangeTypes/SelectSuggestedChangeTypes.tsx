import { useEffect, useMemo, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import styles from './SelectSuggestedChangeTypes.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { getChangeRequestType } from 'core/API/iambicRequest';
import { ChangeType } from '../../types';
import { SELF_SERVICE_STEPS } from '../../constants';
import { Card } from 'shared/layout/Card';
import { Search } from 'shared/form/Search';
import { Button } from 'shared/elements/Button';
import { Link } from 'react-router-dom';

let SUGGESTED_CHANGES = [
  {
    id: 1,
    name: 'Base Application Policy',
    description: 'Provides access to essential services like S3, RDS, and EC2.',
    request_type_id: 1
  },
  {
    id: 2,
    name: 'Lambda with EventBridge',
    description: 'Lambda Permissions with EventBridge',
    request_type_id: 1
  },
  {
    id: 3,
    name: 'App-Specific Lambda',
    description:
      'Create, update, and manage a Lambda function specific to the application.',
    request_type_id: 1
  },
  {
    id: 4,
    name: 'Create/Manage KMS-Encrypted S3 Bucket',
    description:
      'Allows creating and managing an S3 bucket encrypted with AWS Key Management Service (KMS).',
    request_type_id: 1
  },
  {
    id: 5,
    name: 'Manage SQS and SNS',
    description:
      'Enables creating, sending, receiving, and managing messages in SQS queues and SNS topics.',
    request_type_id: 1
  },
  {
    id: 6,
    name: 'Access to Cyberdyne Data (S3/Glue)',
    description:
      'Provides access to Cyberdyne Data, including S3 buckets and AWS Glue data catalog.',
    request_type_id: 1
  },
  {
    id: 7,
    name: 'Manage DynamoDB Tables',
    description:
      'Allows creating, updating, and deleting DynamoDB tables for the application.',
    request_type_id: 1
  },
  {
    id: 8,
    name: 'Manage CloudFormation Stacks',
    // eslint-disable-next-line max-len
    description:
      'Enables creating, updating, and deleting CloudFormation stacks for deploying application resources.',
    request_type_id: 1
  },
  {
    id: 9,
    name: 'Manage Redshift Clusters',
    description:
      'Ability to create, modify, and delete Amazon Redshift clusters for data warehousing.',
    request_type_id: 1
  },
  {
    id: 10,
    name: 'Manage EMR Clusters',
    description:
      'Enables starting, stopping, and terminating Amazon EMR clusters for big data processing.',
    request_type_id: 1
  }
];

const SelectSuggestedChangeTypes = () => {
  const [, setSelectedChangeType] = useState<ChangeType | null>(null);
  const {
    actions: { setCurrentStep }
  } = useContext(SelfServiceContext);
  const {
    store: { selfServiceRequest }
  } = useContext(SelfServiceContext);

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

  useEffect(() => {
    if (changeTypes) {
      console.log('HERE', changeTypes);
      setSuggestedChangeTypes(changeTypes?.data.concat(SUGGESTED_CHANGES));
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
              setCurrentStep(SELF_SERVICE_STEPS.SELECT_IDENTITY);
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
              color="secondary"
              className={`${styles.card}`}
              key={changeType.id}
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

export default SelectSuggestedChangeTypes;
