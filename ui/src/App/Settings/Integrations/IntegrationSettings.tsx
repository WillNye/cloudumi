import { useEffect, useMemo, useRef, useState } from 'react';
import IntegrationCard from './components/IntegrationCard/IntegrationCard';
// import slackIcon from 'assets/integrations/slackIcon.svg';
import awsIcon from 'assets/integrations/awsIcon.svg';
// import gcpIcon from 'assets/integrations/gcpIcon.svg';
// import azureIcon from 'assets/integrations/azureIcon.svg';
import githubIcon from 'assets/integrations/githubIcon.svg';
import SectionHeader from 'shared/elements/SectionHeader/SectionHeader';
// import SlackIntegrationModal from './components/SlackIntegrationsModal';
import GithubIntegrationModal from './components/GithubIntegrationsModal';
import {
  getSlackInstallationStatus,
  getGithubInstallationStatus
} from 'core/API/integrations';
import {
  AWS_CARD_DESCRIPTION,
  // AZURE_CARD_DESCRIPTION,
  CLOUD_PROVIDER_SECTION_DESCRIPTION,
  // GENERAL_SECTION_DESCRPTION,
  GENERAL_SECTION_DESCRPTION_WITHOUT_SLACK,
  GITHUB_CARD_DESCRIPTION
  // GOOGLE_WORKSPACE_CARD_DESCRIPTION,
  // SLACK_CARD_DESCRIPTION
} from './constants';
import { useQuery } from '@tanstack/react-query';
import { useSetState } from 'react-use';
import Joyride, { CallBackProps, Step } from 'react-joyride';
import styles from './IntegrationSettings.module.css';
import { theme } from 'shared/utils/DesignTokens';
import { useSearchParams } from 'react-router-dom';

interface ITourState {
  run: boolean;
  steps: Step[];
}

const IntegrationSettings = () => {
  const awsConfigRef = useRef();
  const [showSlackModal, setShowSlackModal] = useState(false);
  const [showGithubModal, setShowGithubModal] = useState(false);

  const [searchParams] = useSearchParams();
  const showTour = useMemo(
    () => Boolean(searchParams.get('onboarding')),
    [searchParams]
  );

  const [{ run, steps }, setState] = useSetState<ITourState>({
    run: false,
    steps: []
  });

  useEffect(() => {
    if (awsConfigRef?.current && showTour) {
      setState({
        run: true,
        steps: [
          {
            target: awsConfigRef.current,
            content: (
              <p>
                Please click on the &apos;Configure&apos; button to set up your
                AWS settings and add a new hub role to connect to AWS.
              </p>
            ),
            title: 'Setup AWS',
            placement: 'bottom',
            disableBeacon: true,
            disableOverlayClose: true,
            hideCloseButton: true,
            hideFooter: true,
            spotlightClicks: true,
            styles: {
              options: {
                zIndex: 10000,
                arrowColor: theme.colors.gray[600],
                backgroundColor: theme.colors.gray[600],
                primaryColor: theme.colors.blue[600],
                textColor: theme.colors.white,
                overlayColor: theme.colors.gray[700],
                width: '450px'
              }
            }
          }
        ]
      });
    }
    return () => setState({ run: false });
  }, [awsConfigRef, setState, showTour]);

  const {
    refetch: getIntegrationStatus,
    isLoading,
    data: slackData
  } = useQuery({
    queryFn: getSlackInstallationStatus,
    queryKey: ['integrationsStatuses']
  });

  const {
    refetch: getGithubIntegrationStatus,
    isLoading: githubIsLoading,
    data: githubData
  } = useQuery({
    queryFn: getGithubInstallationStatus,
    queryKey: ['githubIntegrationStatus']
  });

  const isSlackConnected = useMemo(
    () => slackData?.data?.installed,
    [slackData]
  );
  const isGithubConnected = useMemo(
    () => githubData?.data?.installed,
    [githubData]
  );

  return (
    <div className={styles.container}>
      <Joyride
        hideCloseButton
        run={run}
        hideBackButton
        steps={steps}
        styles={{
          options: {
            zIndex: 10000,
            arrowColor: theme.colors.gray[200],
            backgroundColor: theme.colors.gray[700],
            primaryColor: theme.colors.blue[600],
            textColor: theme.colors.gray[100],
            overlayColor: theme.colors.gray[600]
          }
        }}
      />
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
            ref={awsConfigRef}
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
        <SectionHeader
          title="General"
          subtitle={GENERAL_SECTION_DESCRPTION_WITHOUT_SLACK}
        />
        <div className={styles.gridContainer}>
          {/* <IntegrationCard
            description={SLACK_CARD_DESCRIPTION}
            title="Connect to Slack"
            icon={slackIcon}
            buttonText={isSlackConnected ? 'Connected' : 'Connect'}
            handleConnect={() => setShowSlackModal(true)}
          /> */}
          <IntegrationCard
            description={GITHUB_CARD_DESCRIPTION}
            title="Connect to Github"
            icon={githubIcon}
            buttonText="Connect"
            handleConnect={() => setShowGithubModal(true)}
          />
        </div>
      </div>
      {/* <SlackIntegrationModal
        showDialog={showSlackModal}
        setShowDialog={setShowSlackModal}
        isSlackConnected={isSlackConnected}
        checkStatus={getIntegrationStatus}
        isGettingIntegrations={isLoading}
      /> */}
      <GithubIntegrationModal
        showDialog={showGithubModal}
        setShowDialog={setShowGithubModal}
        isGithubConnected={isGithubConnected}
        checkStatus={getGithubIntegrationStatus}
        isGettingIntegrations={githubIsLoading}
      />
    </div>
  );
};

export default IntegrationSettings;
