import { useState, useEffect, useCallback, Dispatch, FC } from 'react';
import { getCloudFormationUrl } from '../../utils';
import { Button } from 'shared/elements/Button';
import { generateAWSLoginLink } from 'core/API/awsConfig';
import { Notification, NotificationType } from 'shared/elements/Notification';
import styles from './CreateAWSStack.module.css';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { MODES } from '../../constants';
import useCopyToClipboard from 'core/hooks/useCopyToClipboard';

interface CreateAWSStackProps {
  accountName: string;
  setIsLoading: Dispatch<boolean>;
  isHubAccount: boolean;
  selectedMode: MODES;
}

const CreateAWSStack: FC<CreateAWSStackProps> = ({
  accountName,
  setIsLoading,
  isHubAccount,
  selectedMode
}) => {
  const [generateLinkError, setGenerateLinkError] = useState(null);
  const [cloudFormationUrl, setCloudFormationUrl] = useState('');
  const [copiedText, setCopyText] = useCopyToClipboard();

  useEffect(function onMount() {
    setGenerateLinkError(null);
    getAWSLoginLink();
    return () => {
      setGenerateLinkError(null);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const getAWSLoginLink = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await generateAWSLoginLink(accountName);
      const data = res.data;
      const url = getCloudFormationUrl(data.data, selectedMode, isHubAccount);
      setCloudFormationUrl(url);
      setIsLoading(false);
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setGenerateLinkError(errorMsg || 'Unable to generate AWS Login Link');
      setIsLoading(false);
    }
  }, [accountName, isHubAccount, selectedMode, setIsLoading]);

  const handleClick = () => {
    window.open(cloudFormationUrl, '_blank');
  };

  return (
    <div className={styles.connectStack}>
      <br />

      <h4>1. Login to your chosen AWS Account</h4>
      <br />

      <div className={styles.awsActions}>
        <Button color="primary" onClick={handleClick}>
          Login to {accountName}
        </Button>
        <Button
          color={copiedText ? 'secondary' : 'primary'}
          onClick={() => setCopyText(cloudFormationUrl)}
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

      <br />
      <h4>2. ‘CREATE STACK’ in that account</h4>

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
