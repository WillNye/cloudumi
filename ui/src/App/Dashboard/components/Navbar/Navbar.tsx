import { Icon } from '../../../../shared/elements/Icon';
import { Tooltip } from '../../../../shared/elements/Tooltip';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Logo from '../../../../assets/brand/mark.svg';
import { Avatar } from '../../../../shared/elements/Avatar';
import { Menu } from 'shared/layers/Menu';
import { useRef, useState } from 'react';
import { Button } from '../../../../shared/elements/Button';
import { useAuth } from 'core/Auth';
import { LineBreak } from '../../../../shared/elements/LineBreak';
import { Divider } from '../../../../shared/elements/Divider';
import styles from './Navbar.module.css';
import classNames from 'classnames';

export const Navbar = () => {
  const [open, setOpen] = useState(false);

  const buttonRef = useRef(null);

  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { user } = useAuth();

  return (
    <aside className={styles.sidebar}>
      <Link to="/">
        <div className={styles.sidebarLogo}>
          <img src={Logo} alt="Logo" />
        </div>
      </Link>
      <nav className={styles.sidebarNav}>
        <Link to="/">
          <Tooltip text="Access" alignment="right">
            <div
              className={classNames({ [styles.isActive]: pathname === '/' })}
            >
              <Icon name="access" width="26px" height="26px" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/resources">
          <Tooltip text="Resources" alignment="right">
            <div
              className={classNames({
                [styles.isActive]: (pathname || '').startsWith('/resources')
              })}
            >
              <Icon width="26px" height="26px" name="resource" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/requests">
          <Tooltip text="Requests" alignment="right">
            <div
              className={classNames({
                [styles.isActive]: (pathname || '').startsWith('/requests')
              })}
            >
              <Icon width="26px" height="26px" name="requests" />
            </div>
          </Tooltip>
        </Link>
        {/* <Link to="/findings">
          <Tooltip text="Findings" alignment="right">
            <div
              className={classNames({
                [styles.isActive]: (pathname || '').startsWith('/findings')
              })}
            >
              <Icon width="26px" height="26px" name="asterisk" />
            </div>
          </Tooltip>
        </Link> */}
        <Divider />
        <Link to="/settings">
          <Tooltip text="Settings" alignment="right">
            <div
              className={classNames({
                [styles.isActive]: (pathname || '').startsWith('/settings')
              })}
            >
              <Icon width="26px" height="26px" name="settings" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/downloads">
          <Tooltip text="Downloads" alignment="right">
            <div
              className={classNames({
                [styles.isActive]: (pathname || '').startsWith('/downloads')
              })}
            >
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
