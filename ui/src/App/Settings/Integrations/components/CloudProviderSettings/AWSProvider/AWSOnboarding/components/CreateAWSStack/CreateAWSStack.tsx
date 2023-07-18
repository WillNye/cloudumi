import { useState, useEffect, Dispatch, FC } from 'react';
import { getCloudFormationUrl } from '../../utils';
import { Button } from 'shared/elements/Button';
import { generateAWSLoginLink } from 'core/API/awsConfig';
import { Notification, NotificationType } from 'shared/elements/Notification';
import styles from './CreateAWSStack.module.css';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { MODES } from '../../constants';
import useCopyToClipboard from 'core/hooks/useCopyToClipboard';
import { LineBreak } from 'shared/elements/LineBreak';
import { useQuery } from '@tanstack/react-query';

interface CreateAWSStackProps {
  accountName: string;
  setIsLoading: Dispatch<boolean>;
  isHubAccount: boolean;
  selectedMode: MODES;
  canContinue: (can: boolean) => void;
}

const CreateAWSStack: FC<CreateAWSStackProps> = ({
  accountName,
  setIsLoading,
  isHubAccount,
  selectedMode,
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  canContinue = can => {}
}) => {
  const [generateLinkError, setGenerateLinkError] = useState(null);
  const [cloudFormationUrl, setCloudFormationUrl] = useState('');
  const [copiedText, setCopyText] = useCopyToClipboard();

  useQuery({
    queryFn: generateAWSLoginLink,
    queryKey: ['generateAWSLoginLink', accountName],
    onSuccess: data => {
      const url = getCloudFormationUrl(data.data, selectedMode, isHubAccount);
      setCloudFormationUrl(url);
    },
    onError: (err: AxiosError) => {
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setGenerateLinkError(errorMsg || 'Unable to generate AWS Login Link');
      setIsLoading(false);
    },
    onSettled: () => {
      setIsLoading(false);
    }
  });

  useEffect(
    function onMount() {
      setGenerateLinkError(null);
      setIsLoading(true);
      return () => {
        setGenerateLinkError(null);
      };
    },
    [setIsLoading]
  );

  const handleClick = () => {
    canContinue(true);
    window.open(cloudFormationUrl, '_blank');
  };

  const handleCopyText = () => {
    canContinue(true);
    setCopyText(cloudFormationUrl);
  };

  return (
    <div className={styles.connectStack}>
      <br />

      <h4>1. Login to your chosen AWS Account</h4>
      <br />

      <div className={styles.awsActions}>
        <Button color="primary" onClick={handleClick}>
          Open URL for {accountName}
        </Button>
        <Button
          color={copiedText ? 'secondary' : 'primary'}
          onClick={handleCopyText}
        >
          {copiedText ? 'URL Copied!' : 'Copy URL'}
        </Button>
      </div>

      {generateLinkError && (
        <Notification
          type={NotificationType.ERROR}
          header="Unable to generate AWs login link"
        >
          {generateLinkError}
        </Notification>
      )}
      <LineBreak />
      <h4>2. ‘CREATE STACK’ in that account</h4>
      <br />
      <p>
        This will create a CloudFormation stack in your AWS account. This stack
        will have read-only access to your cloud resources, and the ability to
        assume roles that you explicitly provide access to.
      </p>
      <br />

      <div className={styles.header}>
        <h5>What to expect in AWS</h5>
      </div>
      <div className={styles.warningAlert}>
        <ul>
          <li>
            Select{' '}
            <strong>
              <i>
                ‘I acknowledge that AWS CloudFormation might create IAM
                resources with custom names’
              </i>
            </strong>{' '}
            and click <strong>Create Stack.</strong>
          </li>

          <li>
            When all resources have the status <strong>CREATE_COMPLETE</strong>,
            click ‘Next’.
          </li>
        </ul>
      </div>
    </div>
  );
};

export default CreateAWSStack;
