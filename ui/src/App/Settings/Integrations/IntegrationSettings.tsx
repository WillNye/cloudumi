import styles from './IntegrationSettings.module.css';
import { useMemo, useState } from 'react';
import IntegrationCard from './components/IntegrationCard/IntegrationCard';
import slackIcon from 'assets/integrations/slackIcon.svg';
import awsIcon from 'assets/integrations/awsIcon.svg';
// import gcpIcon from 'assets/integrations/gcpIcon.svg';
// import azureIcon from 'assets/integrations/azureIcon.svg';
import githubIcon from 'assets/integrations/githubIcon.svg';
import oktaIcon from 'assets/integrations/oktaIcon.svg';
import SectionHeader from 'shared/elements/SectionHeader/SectionHeader';
import SlackIntegrationModal from './components/SlackIntegrationsModal';
import { getSlackInstallationStatus } from 'core/API/integrations';
import {
  AWS_CARD_DESCRIPTION,
  // AZURE_CARD_DESCRIPTION,
  CLOUD_PROVIDER_SECTION_DESCRIPTION,
  GENERAL_SECTION_DESCRPTION,
  GITHUB_CARD_DESCRIPTION,
  // GOOGLE_WORKSPACE_CARD_DESCRIPTION,
  OKTA_CARD_DESCRIPTION,
  SLACK_CARD_DESCRIPTION
} from './constants';
import { useQuery } from '@tanstack/react-query';

const IntegrationSettings = () => {
  const [showSlackModal, setShowSlackModal] = useState(false);

  const {
    refetch: getIntegrationStatus,
    isLoading,
    data
  } = useQuery({
    queryFn: getSlackInstallationStatus,
    queryKey: ['integrationsStatuses']
  });

  const isSlackConnected = useMemo(() => data?.data?.installed, [data]);

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <SectionHeader
          title="Cloud Providers"
          subtitle={CLOUD_PROVIDER_SECTION_DESCRIPTION}
        />
        <div className={styles.gridContainer}>
          <IntegrationCard
            description={AWS_CARD_DESCRIPTION}
            title="Configure AWS"
            icon={awsIcon}
            buttonText="Configure"
            link="/settings/integrations/aws"
          />
          {/* <IntegrationCard
            description={GOOGLE_WORKSPACE_CARD_DESCRIPTION}
            title="Configure GCP"
            icon={gcpIcon}
            buttonText="Configure"
            disableBtn
          />
          <IntegrationCard
            description={AZURE_CARD_DESCRIPTION}
            title="Configure Azure"
            icon={azureIcon}
            buttonText="Configure"
            disableBtn
          /> */}
        </div>
        <SectionHeader title="General" subtitle={GENERAL_SECTION_DESCRPTION} />
        <div className={styles.gridContainer}>
          <IntegrationCard
            description={SLACK_CARD_DESCRIPTION}
            title="Connect to Slack"
            icon={slackIcon}
            buttonText={isSlackConnected ? 'Connected' : 'Connect'}
            handleConnect={() => setShowSlackModal(true)}
          />
          <IntegrationCard
            description={GITHUB_CARD_DESCRIPTION}
            title="Connect to Github"
            icon={githubIcon}
            buttonText="Connect"
            disableBtn
          />
        </div>
        <SectionHeader
          title="SCIM/SSO"
          subtitle="Set up Single Sign-On (SSO) and System for Cross-domain Identity
        Management (SCIM) integrations, receive notifications, and connect with
        cloud providers for secure and streamlined operations."
        />
        <div className={styles.gridContainer}>
          <IntegrationCard
            description={OKTA_CARD_DESCRIPTION}
            title="Connect to OKta"
            icon={oktaIcon}
            buttonText="Connect"
            disableBtn
          />
        </div>
      </div>
      <SlackIntegrationModal
        showDialog={showSlackModal}
        setShowDialog={setShowSlackModal}
        isSlackConnected={isSlackConnected}
        checkStatus={getIntegrationStatus}
        isGettingIntegrations={isLoading}
      />
    </div>
  );
};

export default IntegrationSettings;
