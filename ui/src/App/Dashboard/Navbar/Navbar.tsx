import { Link } from 'react-router-dom';
import styles from './Navbar.module.css';
import { Icon } from '../../../shared/elements/Icon';
import { Tooltip } from '../../../shared/elements/Tooltip';
import Logo from '../../../assets/brand/mark.svg';
import { Avatar } from '../../../shared/elements/Avatar';

export const Navbar = () => {
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
        <Link to="/request">
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
        <Avatar name="Sula" />
      </div>
    </aside>
  );
};

// export default Sidebar;
