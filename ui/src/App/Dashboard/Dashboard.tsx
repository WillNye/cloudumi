import { Outlet } from 'react-router';
import Joyride, { CallBackProps, STATUS, Step } from 'react-joyride';
import { Navbar } from './components/Navbar';
import styles from './Dashboard.module.css';
import {
  Notification,
  NotificationPosition,
  NotificationType
} from 'shared/elements/Notification';
import { useMount, useSetState } from 'react-use';
import { theme } from 'shared/utils/DesignTokens';
import { Button } from 'shared/elements/Button';
import { tourSteps } from './components/DashboardTourSteps';
import { useAuth } from 'core/Auth';

interface ITourState {
  run: boolean;
  steps: Step[];
}

export const Dashboard = () => {
  const [{ run, steps }, setState] = useSetState<ITourState>({
    run: true,
    steps: tourSteps
  });

  const { isHubAccountInstalled, isGithubInstalled } = useAuth();

  console.log(
    isGithubInstalled,
    '----------------------',
    isHubAccountInstalled
  );

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status, type } = data;
    const finishedStatuses: string[] = [STATUS.FINISHED, STATUS.SKIPPED];

    if (finishedStatuses.includes(status)) {
      setState({ run: false });
    }
  };

  return (
    <div className={styles.dashboard}>
      {/* <Notification
          header="test"
          type={NotificationType.INFO}
          position={NotificationPosition.FLOATING}
          fullWidth
          showCloseIcon
        ></Notification> */}
      <Navbar />
      <main className={styles.mainContent}>
        <Joyride
          callback={handleJoyrideCallback}
          continuous
          hideCloseButton
          run={false}
          // scrollToFirstStep
          // showProgress
          // showSkipButton
          hideBackButton
          steps={steps}
          styles={{
            options: {
              zIndex: 10000,
              arrowColor: theme.colors.gray[200],
              backgroundColor: theme.colors.gray[700],
              primaryColor: theme.colors.blue[600],
              textColor: theme.colors.gray[100],
              // width: 650,
              overlayColor: theme.colors.gray[600]
            }
          }}
        />
        <Outlet />
      </main>
    </div>
  );
};
