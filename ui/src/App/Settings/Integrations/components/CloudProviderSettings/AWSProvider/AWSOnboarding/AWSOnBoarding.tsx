import { useState, useMemo, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ConnectionMethod from './components/ConnectionMethod';
import ConfigureAccount from './components/ConfigureAccount';
import HorizontalStepper from './components/HorizontalStepper';
import CreateAWSStack from './components/CreateAWSStack/CreateAWSStack';
import CheckAccountConnection from './components/CheckAccountConnection';
import {
  ACCOUNT_NAME_REGEX,
  MODES,
  ONBOARDING_SECTIONS,
  ONBOARDING_STEPS
} from './constants';
import { getHubAccounts } from 'core/API/awsConfig';
import { Icon } from 'shared/elements/Icon';
import { Button } from 'shared/elements/Button';
import { Loader } from 'shared/elements/Loader';
import classNames from 'classnames';
import AWSMxNetImg from 'assets/vendor/mx-net.svg';
import AWSCacheImg from 'assets/vendor/cdk.svg';
import styles from './AWSOnBoarding.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useQuery } from '@tanstack/react-query';

const OnBoarding = () => {
  const { CONNECTION_METHOD, CONFIGURE, CREATE_STACK, STATUS } =
    ONBOARDING_SECTIONS;

  const [isConnected, setIsConnected] = useState(false);
  const [activeId, setActiveId] = useState(CONNECTION_METHOD.id);
  const [accountName, setAccountName] = useState('');
  const [selectedMode, setSelectedMode] = useState(MODES.READ_WRTE);
  const [isLoading, setIsLoading] = useState(false);
  const [isHubAccount, setIsHubAccount] = useState(true);

  const { isLoading: isFetchingData } = useQuery({
    queryFn: getHubAccounts,
    queryKey: ['getHubAccounts'],
    onSuccess: data => {
      if (data && data.count) {
        setIsHubAccount(false);
      }
    }
  });

  const handleModeChange = ({ target: { value } }) => setSelectedMode(value);

  const handleAccNameChange = event => {
    event.preventDefault();
    const { value } = event.target;
    if (ACCOUNT_NAME_REGEX.test(value)) {
      setAccountName(value);
    }
  };

  const activeSection = useMemo(() => {
    const sections = {
      [CONNECTION_METHOD.id]: <ConnectionMethod />,
      [CONFIGURE.id]: (
        <ConfigureAccount
          handleAccNameChange={handleAccNameChange}
          handleModeChange={handleModeChange}
          accountName={accountName}
          selectedMode={selectedMode}
        />
      ),
      [CREATE_STACK.id]: (
        <CreateAWSStack
          accountName={accountName}
          setIsLoading={setIsLoading}
          selectedMode={selectedMode}
          isHubAccount={isHubAccount}
        />
      ),
      [STATUS.id]: (
        <CheckAccountConnection
          setIsConnected={setIsConnected}
          isHubAccount={isHubAccount}
          accountName={accountName}
        />
      )
    };
    return sections[activeId];
  }, [activeId, accountName, selectedMode, isHubAccount]); // eslint-disable-line react-hooks/exhaustive-deps

  const overLayClasses = useMemo(
    () =>
      classNames(styles.loaderOverlay, {
        [styles.disabled]: !isLoading || !isFetchingData
      }),
    [isLoading, isFetchingData]
  );

  const isNextDisabled = useMemo(() => {
    return activeId === CONFIGURE.id && !accountName;
  }, [accountName, activeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const connectedComponent = useMemo(
    () => (
      <div className={styles.connectingAccount}>
        <h2>Successfully Connected</h2>
        <LineBreak size="large" />
        <div>
          <div className={styles.loaderActions}>
            <img src={AWSCacheImg} className={styles.icon} />
            <div>
              <h3>Onboarding account</h3>
              <p>
                Complete. You can view your account details in{' '}
                <Link to="/settings/integrations">Settings.</Link>
              </p>
            </div>
          </div>
          <LineBreak size="large" />
          <div className={styles.loaderActions}>
            <img src={AWSMxNetImg} className={styles.icon} />
            <div>
              <h3>Caching resources</h3>
              <p>
                Started caching resources (This may take a while). You may leave
                this page and continue using the application
              </p>
            </div>
          </div>
        </div>
      </div>
    ),
    []
  );

  return (
    <div className={styles.onboarding}>
      {isConnected ? (
        connectedComponent
      ) : (
        <>
          <div className={styles.documentation}>
            <Link to="/docs" target="_blank" rel="noopener noreferrer">
              <Icon name="file outline" /> Documentation
            </Link>
          </div>

          <h2 className={styles.header}>Connect Noq to AWS</h2>
          <HorizontalStepper activeId={activeId} steps={ONBOARDING_STEPS} />
          <div className={styles.mainContent}>
            <Loader className={overLayClasses} />
            {activeSection}
          </div>
          <div className={styles.actionsWrapper}>
            <div className={styles.actions}>
              {activeId !== CONNECTION_METHOD.id && (
                <Button onClick={() => setActiveId(activeId - 1)}>Back</Button>
              )}
              {activeId !== STATUS.id && (
                <Button
                  color="primary"
                  onClick={() => setActiveId(activeId + 1)}
                  disabled={isNextDisabled}
                >
                  Next
                </Button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default OnBoarding;
