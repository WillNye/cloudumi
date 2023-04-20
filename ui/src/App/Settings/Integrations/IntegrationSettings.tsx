import styles from './IntegrationSettings.module.css';
import { INTEGRATIONS_TABS } from './constants';
import { useEffect, useState } from 'react';
import IntegrationCard from './components/IntegrationCard/IntegrationCard';
import slackIcon from 'assets/integrations/slackIcon.svg';
import awsIcon from 'assets/integrations/awsIcon.svg';
import gcpIcon from 'assets/integrations/gcpIcon.svg';
import azureIcon from 'assets/integrations/azureIcon.svg';
import githubIcon from 'assets/integrations/githubIcon.svg';
import oktaIcon from 'assets/integrations/oktaIcon.svg';
import SectionHeader from 'shared/elements/SectionHeader/SectionHeader';
import SlackIntegrationModal from './components/SlacKIntegrationsModal/SlackIntegrationModal';
import { getSlackInstallationStatus } from 'core/API/integrations';

const IntegrationSettings = () => {
  const [showSlackModal, setShowSlackModal] = useState(false);
  const [isSlackConnected, setIsSlackConnected] = useState(false);

  useEffect(() => {
    getSlackInstallationStatus()
      .then(({ data }) => {
        setIsSlackConnected(data.data.installed);
      })
      .catch(() => ({
        // TODO handle error
      }));
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <SectionHeader
          title="Cloud Providers"
          subtitle="Configure and connect with cloud service providers (CSPs) to take advantage of benefits such as improved manageability, greater transparency, and the implementation of robust security measures, including the principle of least privilege."
        />
        <div className={styles.gridContainer}>
          <IntegrationCard
            description="Amazon Web Services (AWS) is a cloud-based platform that provides a range of services, including compute, storage, and databases, to help businesses scale and grow."
            title="Configure AWS"
            icon={awsIcon}
            buttonText="Configure"
            link="/settings/integrations/aws"
          />
          <IntegrationCard
            description="Google Cloud Platform (GCP) is a cloud-based platform that provides a range of services, including computing, storage, and networking, to help businesses build, deploy, and scale applications."
            title="Configure GCP"
            icon={gcpIcon}
            buttonText="Configure"
            disableBtn
          />
          <IntegrationCard
            description="Microsoft Azure is a cloud computing platform that provides a range of services, including virtual machines, databases, and developer tools, to help businesses build and deploy applications."
            title="Configure Azure"
            icon={azureIcon}
            buttonText="Configure"
            disableBtn
          />
        </div>
        <SectionHeader
          title="General"
          subtitle="Integrating Slack and GitHub can help streamline your workflow, improve team collaboration, and increase productivity. With a Slack and GitHub integration, you can receive notifications directly in Slack when new code is pushed, pull requests are created, or issues are opened or closed in GitHub."
        />
        <div className={styles.gridContainer}>
          <IntegrationCard
            description="Collaborate efficiently with Slack. Receive real-time notifications when new code is pushed, pull requests are created, or issues are opened or closed."
            title="Connect to Slack"
            icon={slackIcon}
            buttonText={isSlackConnected ? 'Connected' : 'Connect'}
            handleConnect={() => setShowSlackModal(true)}
          />
          <IntegrationCard
            description="Streamline your workflow with GitHub. Automate tasks such as creating pull requests, and receive notifications when new code is pushed, pull requests are created, or issues are opened or closed."
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
            description="Okta provides cloud-based identity and access management to secure your applications, data, and infrastructure. Manage user access and authentication across multiple applications from a central location, reducing the risk of data breaches."
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
        setIsSlackConnected={setIsSlackConnected}
      />
    </div>
  );
};

export default IntegrationSettings;
