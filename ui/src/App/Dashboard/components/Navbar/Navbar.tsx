import { Icon } from '../../../../shared/elements/Icon';
import { Tooltip } from '../../../../shared/elements/Tooltip';
import { Link, useNavigate } from 'react-router-dom';
import styles from './Navbar.module.css';
import Logo from '../../../../assets/brand/mark.svg';
import { Avatar } from '../../../../shared/elements/Avatar';
import { Menu } from 'shared/layers/Menu';
import { useRef, useState } from 'react';
import { Button } from '../../../../shared/elements/Button';
import { useAuth } from 'core/Auth';
import { LineBreak } from '../../../../shared/elements/LineBreak';
import { Divider } from '../../../../shared/elements/Divider';
import { useMount, useSetState } from 'react-use';
import Joyride, {
  ACTIONS,
  CallBackProps,
  EVENTS,
  STATUS,
  Step
} from 'react-joyride';
import { theme } from 'shared/utils/DesignTokens';

interface State {
  run: boolean;
  stepIndex: number;
  steps: Step[];
}

const commonProps: Partial<Step> = {
  disableBeacon: true,
  disableOverlayClose: true,
  hideCloseButton: true,
  hideBackButton: true,
  placement: 'right',
  spotlightClicks: true,
  showProgress: false,
  styles: {
    options: {
      zIndex: 10000,
      arrowColor: theme.colors.gray[600],
      backgroundColor: theme.colors.gray[600],
      primaryColor: theme.colors.blue[600],
      textColor: theme.colors.white,
      overlayColor: theme.colors.gray[700]
    }
  }
};

export const Navbar = () => {
  const [open, setOpen] = useState(false);
  const [{ run, stepIndex, steps }, setState] = useSetState<State>({
    run: false,
    stepIndex: 0,
    steps: []
  });
  const buttonRef = useRef(null);

  const { user } = useAuth();

  const navigate = useNavigate();

  const settingsRef = useRef<HTMLAnchorElement>(null);

  useMount(() => {
    setState({
      run: true,
      steps: [
        {
          content:
            'You can interact with your own components through the spotlight.',
          ...commonProps,
          target: settingsRef.current!,
          locale: { last: 'Next' },
          title: 'Welcome'
        }
      ]
    });
  });

  const handleJoyrideCallback = () => {
    setState({ run: false, stepIndex: 0 });
    navigate('/settings');
  };

  return (
    <aside className={styles.sidebar}>
      <Joyride
        callback={handleJoyrideCallback}
        continuous
        run={run}
        scrollToFirstStep
        showProgress
        showSkipButton
        stepIndex={stepIndex}
        steps={steps}
      />
      <Link to="/">
        <div className={styles.sidebarLogo}>
          <img src={Logo} alt="Logo" />
        </div>
      </Link>
      <nav className={styles.sidebarNav}>
        <Link to="/">
          <Tooltip text="Access" alignment="right">
            <div>
              <Icon name="lock" width="26px" height="26px" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/resources">
          <Tooltip text="Resources" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="resource" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/requests">
          <Tooltip text="Requests" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="pointer" />
            </div>
          </Tooltip>
        </Link>
        <Link
          to="/settings"
          ref={settingsRef}
          onClick={() => setState({ run: false, stepIndex: 0 })}
        >
          <Tooltip text="Settings" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="settings" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/downloads">
          <Tooltip text="Downloads" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="download" />
            </div>
          </Tooltip>
        </Link>
      </nav>
      <div className={styles.user}>
        <Avatar
          name={user.user}
          ref={buttonRef}
          onClick={() => setOpen(!open)}
          className={styles.cursorPointer}
        />
        <Menu
          placement="left"
          open={open}
          onClose={() => setOpen(false)}
          reference={buttonRef}
        >
          <div className={styles.dropdownContent}>
            <div className={styles.dropdownItem}>
              <Avatar name={user.user} size="small" />
              <div className={styles.dropdownText}>{user.user}</div>
            </div>
            <LineBreak size="small" />
            <div
              className={`${styles.dropdownItem} ${styles.cursorPointer}`}
              onClick={() => navigate('/settings')}
            >
              <Icon name="settings" size="medium" />
              <div>Settings</div>
            </div>
            <Divider />
            <LineBreak size="small" />
            <Button
              size="small"
              fullWidth
              color="secondary"
              variant="outline"
              onClick={() => navigate('/logout')}
            >
              <span className={styles.btnContent}>
                <Icon name="logout" size="medium" />
                <span className={styles.btnText}>Logout</span>
              </span>
            </Button>
          </div>
        </Menu>
      </div>
    </aside>
  );
};
