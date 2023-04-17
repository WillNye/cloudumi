import { Button } from 'shared/elements/Button';
import styles from './IntegrationSettings.module.css';
import { INTEGRATIONS_TABS } from './constants';
import { useState } from 'react';
import IntegrationCard from './components/IntegrationCard/IntegrationCard';
import slackIcon from 'assets/integrations/slackIcon.svg';
import awsIcon from 'assets/integrations/awsIcon.svg';
import gcpIcon from 'assets/integrations/gcpIcon.svg';
import azureIcon from 'assets/integrations/azureIcon.svg';
import githubIcon from 'assets/integrations/githubIcon.svg';

const IntegrationSettings = () => {
  const [currentTab, setCurrentTab] = useState<INTEGRATIONS_TABS>(
    INTEGRATIONS_TABS.AUTHENTICATION
  );

  return (
    <div className={styles.container}>
      <p>
        Set up Single Sign-On (SSO) and System for Cross-domain Identity
        Management (SCIM) integrations, receive notifications, and connect with
        cloud providers for secure and streamlined operations.
      </p>
      <br />
      <div className={styles.content}>
        <div className={styles.gridContainer}>
          <IntegrationCard
            description="Configure AWS to access team messaging and notifications."
            title="Configure AWS"
            icon={awsIcon}
            buttonText="Configure"
            link="/settings/integrations/aws"
          />
          <IntegrationCard
            description="Configure GCP to access team messaging and notifications."
            title="Configure GCP"
            icon={gcpIcon}
            buttonText="Configure"
            disableBtn
          />
          <IntegrationCard
            description="Configure Azure to access team messaging and notifications."
            title="Configure Azure"
            icon={azureIcon}
            buttonText="Configure"
            disableBtn
          />
        </div>
        <div className={styles.gridContainer}>
          <IntegrationCard
            description="Connect your Slack account to access team messaging and notifications."
            title="Connect to Slack"
            icon={slackIcon}
            buttonText="Connect"
            disableBtn
          />
          <IntegrationCard
            description="Connect your Slack account to access team messaging and notifications."
            title="Connect to Github"
            icon={githubIcon}
            buttonText="Connect"
            disableBtn
          />
        </div>
      </div>
    </div>
  );
};

export default IntegrationSettings;
