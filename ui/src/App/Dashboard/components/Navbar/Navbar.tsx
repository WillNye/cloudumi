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
  hideFooter: true,
  styles: {
    options: {
      zIndex: 10000,
      arrowColor: theme.colors.gray[500],
      backgroundColor: theme.colors.gray[500],
      primaryColor: theme.colors.blue[600],
      textColor: theme.colors.white,
      overlayColor: theme.colors.gray[600]
    },
    buttonNext: {
      backgroundColor: theme.colors.blue[500]
      // outlineColor: theme.colors.gray[500],
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

  const accessRef = useRef<HTMLAnchorElement>(null);
  const resourcesRef = useRef<HTMLAnchorElement>(null);
  const requestsRef = useRef<HTMLAnchorElement>(null);
  const settingsRef = useRef<HTMLAnchorElement>(null);
  const downloadsRef = useRef<HTMLAnchorElement>(null);

  useMount(() => {
    setState({
      run: true,
      steps: [
        {
          content:
            'You can interact with your own components through the spotlight.',
          ...commonProps,
          target: accessRef.current!,
          title: 'Access'
        },
        {
          content: 'This is our sidebar, you can find everything you need here',
          ...commonProps,
          target: resourcesRef.current!,
          title: 'Sidebar'
        },
        {
          content: 'Check the availability of the team!',
          ...commonProps,
          target: requestsRef.current!,
          title: 'The schedule'
        },
        {
          content: <div>Our rate is off the charts!</div>,
          ...commonProps,
          target: settingsRef.current!,
          title: 'Our Growth'
        },
        {
          content: <div>User</div>,
          ...commonProps,
          target: downloadsRef.current!,
          title: 'Our Users'
        }
        // {
        //   content: 'The awesome connections you have made',
        //   placement: 'top',
        //   target: connections.current!,
        // },
      ]
    });

    // a11yChecker();
  });

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { action, index, status, type } = data;

    if (([STATUS.FINISHED, STATUS.SKIPPED] as string[]).includes(status)) {
      // Need to set our running state to false, so we can restart if we click start again.
      setState({ run: false, stepIndex: 0 });
    } else if (
      ([EVENTS.STEP_AFTER, EVENTS.TARGET_NOT_FOUND] as string[]).includes(type)
    ) {
      const nextStepIndex = index + (action === ACTIONS.PREV ? -1 : 1);
      setState({
        stepIndex: nextStepIndex
      });
    }
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
        <Link to="/" ref={accessRef}>
          <Tooltip text="Access" alignment="right">
            <div>
              <Icon name="lock" width="26px" height="26px" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/resources" ref={resourcesRef}>
          <Tooltip text="Resources" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="resource" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/requests" ref={requestsRef}>
          <Tooltip text="Requests" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="pointer" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/settings" ref={settingsRef}>
          <Tooltip text="Settings" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="settings" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/downloads" ref={downloadsRef}>
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
