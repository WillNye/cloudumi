import { Outlet } from 'react-router';
import Joyride, { CallBackProps, STATUS, Step } from 'react-joyride';
import { Navbar } from './components/Navbar';
import { useSetState } from 'react-use';
import { theme } from 'shared/utils/DesignTokens';
import { tourSteps } from './components/DashboardTourSteps';
import { useAuth } from 'core/Auth';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Dashboard.module.css';

interface ITourState {
  run: boolean;
  steps: Step[];
}

export const Dashboard = () => {
  const [{ run, steps }, setState] = useSetState<ITourState>({
    run: false,
    steps: tourSteps
  });

  const { isHubAccountInstalled } = useAuth();
  const navigate = useNavigate();

  useEffect(
    function onMount() {
      const isDoneOnboarding =
        localStorage.getItem('onboarding') === 'complete';
      if (!isHubAccountInstalled && !isDoneOnboarding) {
        setState({ run: true });
      }
    },
    [isHubAccountInstalled, setState]
  );

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status } = data;

    if (status === STATUS.FINISHED) {
      navigate('/settings/integrations?onboarding=true');
      setState({ run: false });
      localStorage.setItem('onboarding', 'complete');
    }
    if (status === STATUS.SKIPPED) {
      setState({ run: false });
      localStorage.setItem('onboarding', 'complete');
    }
  };

  return (
    <div className={styles.dashboard}>
      <Joyride
        callback={handleJoyrideCallback}
        continuous
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
      <Navbar />
      <main className={styles.mainContent}>
        <Outlet />
      </main>
    </div>
  );
};
