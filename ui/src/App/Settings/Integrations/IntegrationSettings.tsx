import { Button } from 'shared/elements/Button';
import styles from './IntegrationSettings.module.css';
import { INTEGRATIONS_TABS } from './constants';
import { useMemo, useState } from 'react';
import NotificationSettings from './components/NotificationSettings';
import AuthenticationSettings from './components/AuthenticationSettings';
import IambicSettings from './components/IambicSettings';
import SlackIntegrations from './components/SlackIntegration/SlackIntegration';
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

      {/* <div>
        <nav className={styles.nav}>
          <ul className={styles.navList}>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.AUTHENTICATION &&
                styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.AUTHENTICATION)}
            >
              <div className={styles.text}>Authentication</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.CLOUD_PROVIDER &&
                styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.CLOUD_PROVIDER)}
            >
              <div className={styles.text}>Cloud Providers</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.NOTIFICATIONS &&
                styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.NOTIFICATIONS)}
            >
              <div className={styles.text}>Notifications</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.IAMBIC && styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.IAMBIC)}
            >
              <div className={styles.text}>Iambic</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.SLACK && styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.SLACK)}
            >
              <div className={styles.text}>Slack</div>
            </li>
          </ul>
        </nav>
      </div> */}
      <div className={styles.content}>
        <div className={styles.gridContainer}>
          <IntegrationCard
            description="Configure AWS to access team messaging and notifications."
            title="Configure AWS"
            icon={awsIcon}
          />
          <IntegrationCard
            description="Configure AWS to access team messaging and notifications."
            title="Configure GCP"
            icon={gcpIcon}
          />
          <IntegrationCard
            description="Configure AWS to access team messaging and notifications."
            title="Configure GCP"
            icon={azureIcon}
          />
        </div>
        <div className={styles.gridContainer}>
          <IntegrationCard
            description="Connect your Slack account to access team messaging and notifications."
            title="Connect to Slack"
            icon={slackIcon}
          />
          <IntegrationCard
            description="Connect your Slack account to access team messaging and notifications."
            title="Connect to Github"
            icon={githubIcon}
          />
        </div>
      </div>
    </div>
  );
};

export default IntegrationSettings;
