import { FC, useState } from 'react';
import { Link, Outlet } from 'react-router-dom';
import appConfigImg from '../../../assets/vendor/app-config.svg';
import styles from './SettingsMenu.module.css';
import { SETTINGS_PAGE_LINKS } from './constants';

const SettingsMenu: FC = () => {
  const [activeLink, setActiveLink] = useState(
    SETTINGS_PAGE_LINKS.PROFILE_SETTINGS
  );

  return (
    <div className={styles.container}>
      <div className={styles.header}>Account Settings</div>
      <p className={styles.description}>
        Manage and customize all aspects of your account and system
        integrations.
      </p>

      <div className={styles.content}>
        <div className={styles.sideNav}>
          <nav className={styles.nav}>
            <ul className={styles.navList}>
              <li className={`${styles.navItem}`}>
                <Link to="/settings">My Profile</Link>
              </li>
              <li className={`${styles.navItem}`}>
                <Link to="/settings/integrations">Integrations</Link>
              </li>
              <li className={`${styles.navItem}`}>
                <Link to="/settings/accounts">Accounts Management</Link>
              </li>
            </ul>
          </nav>
        </div>

        <div className={styles.outlet}>
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default SettingsMenu;
