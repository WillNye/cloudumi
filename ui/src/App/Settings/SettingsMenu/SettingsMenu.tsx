import { FC, useMemo, useState } from 'react';
import { Link, Outlet, useMatch } from 'react-router-dom';
import appConfigImg from '../../../assets/vendor/app-config.svg';
import styles from './SettingsMenu.module.css';
import {
  BREAD_CRUMBS_ACCOUNTS_PATH,
  BREAD_CRUMBS_INTEGRATIONS_PATH,
  BREAD_CRUMBS_PROFILE_PATH,
  BREAD_CRUMBS_SETTINGS_PATH
} from './constants';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';

const SettingsMenu: FC = () => {
  const isMyProfilePath = useMatch('/settings');
  const isIntegrationsPath = useMatch('/settings/integrations');
  const isAccountsPath = useMatch('/settings/user_management');

  const breadCrumbsPaths = useMemo(() => {
    if (isMyProfilePath) {
      return [...BREAD_CRUMBS_SETTINGS_PATH, ...BREAD_CRUMBS_PROFILE_PATH];
    }
    if (isIntegrationsPath) {
      return [...BREAD_CRUMBS_SETTINGS_PATH, ...BREAD_CRUMBS_INTEGRATIONS_PATH];
    }
    return [...BREAD_CRUMBS_SETTINGS_PATH, ...BREAD_CRUMBS_ACCOUNTS_PATH];
  }, [isMyProfilePath, isIntegrationsPath]);

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <div className={styles.sideNav}>
          <nav className={styles.nav}>
            <div className={styles.header}>Settings</div>

            <ul className={styles.navList}>
              <li
                className={`${styles.navItem} ${
                  isMyProfilePath && styles.isActive
                }`}
              >
                <Link to="/settings">My Profile</Link>
              </li>
              <li
                className={`${styles.navItem} ${
                  isIntegrationsPath && styles.isActive
                }`}
              >
                <Link to="/settings/integrations">Integrations</Link>
              </li>
              <li
                className={`${styles.navItem} ${
                  isAccountsPath && styles.isActive
                }`}
              >
                <Link to="/settings/user_management">User Management</Link>
              </li>
            </ul>
          </nav>
        </div>

        <div className={styles.outlet}>
          <Breadcrumbs items={breadCrumbsPaths} />
          <p className={styles.description}>
            Manage and customize all aspects of your account and system
            integrations.
          </p>

          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default SettingsMenu;
