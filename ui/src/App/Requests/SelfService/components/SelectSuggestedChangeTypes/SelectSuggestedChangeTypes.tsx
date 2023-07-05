import { useMemo, useState } from 'react';
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

const SUGGESTED_CHANGES = [
  {
    header: 'Base Application Policy',
    subtext: 'Provides access to essential services like S3, RDS, and EC2.'
  },
  {
    header: 'Lambda with EventBridge',
    subtext: 'Lambda Permissions with EventBridge'
  },
  {
    header: 'App-Specific Lambda',
    subtext:
      'Create, update, and manage a Lambda function specific to the application.'
  },
  {
    header: 'Create/Manage KMS-Encrypted S3 Bucket',
    subtext:
      'Allows creating and managing an S3 bucket encrypted with AWS Key Management Service (KMS).'
  },
  {
    header: 'Manage SQS and SNS',
    subtext:
      'Enables creating, sending, receiving, and managing messages in SQS queues and SNS topics.'
  },
  {
    header: 'Access to Cyberdyne Data (S3/Glue)',
    subtext:
      'Provides access to Cyberdyne Data, including S3 buckets and AWS Glue data catalog.'
  },
  {
    header: 'Manage DynamoDB Tables',
    subtext:
      'Allows creating, updating, and deleting DynamoDB tables for the application.'
  },
  {
    header: 'Manage CloudFormation Stacks',
    subtext:
      'Enables creating, updating, and deleting CloudFormation stacks for deploying application resources.'
  },
  {
    header: 'Manage Redshift Clusters',
    subtext:
      'Ability to create, modify, and delete Amazon Redshift clusters for data warehousing.'
  },
  {
    header: 'Manage EMR Clusters',
    subtext:
      'Enables starting, stopping, and terminating Amazon EMR clusters for big data processing.'
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

  const { data: changeTypes, isLoading } = useQuery({
    queryFn: getChangeRequestType,
    queryKey: ['getChangeRequestType', selectedRequestType?.id],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>What Permissions would you like?</h3>
        <LineBreak size="medium" />
        <div className={styles.link}>
          <a
            href="#"
            onClick={e => {
              e.preventDefault();
              setCurrentStep(SELF_SERVICE_STEPS.SELECT_IDENTITY);
            }}
          >
            I don’t see what I need, let me customize it
          </a>
        </div>
        <br />
        <div className={styles.cardContainer}>
          {SUGGESTED_CHANGES.map(changeType => (
            <Card
              variant="outlined"
              color="secondary"
              className={`${styles.card}`}
              contentClassName={styles.cardContent}
              key={changeType.header}
              clickable
            >
              <h4>{changeType.header}</h4>
              <p>{changeType.subtext}</p>
            </Card>
          ))}
        </div>
      </div>
    </Segment>
  );
};

export default SelectSuggestedChangeTypes;
