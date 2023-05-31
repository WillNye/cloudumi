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

export const Navbar = () => {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);

  const { user } = useAuth();

  const navigate = useNavigate();

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
        <Link to="/profile">
          <Tooltip text="Users" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="profile" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/notifications">
          <Tooltip text="Notifications" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="notifications" />
            </div>
          </Tooltip>
        </Link>
        <Link to="/settings">
          <Tooltip text="Settings" alignment="right">
            <div>
              <Icon width="26px" height="26px" name="settings" />
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
