import { FC, useMemo } from 'react';
import { Link, Outlet, useMatch } from 'react-router-dom';
import styles from './SettingsMenu.module.css';
import {
  BREAD_CRUMBS_ACCOUNTS_PATH,
  BREAD_CRUMBS_AUTH_SETTINGS_PATH,
  BREAD_CRUMBS_INTEGRATIONS_PATH,
  BREAD_CRUMBS_PROFILE_PATH,
  BREAD_CRUMBS_SETTINGS_PATH
} from './constants';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { useAuth } from 'core/Auth';
import classNames from 'classnames';

const SettingsMenu: FC = () => {
  const { user } = useAuth();

  const isMyProfilePath = useMatch('/settings');
  const isIntegrationsPath = useMatch('/settings/integrations');
  const isAccountsPath = useMatch('/settings/user_management');
  const isAuthenticationPath = useMatch('/settings/authentication-settings');

  const breadCrumbsPaths = useMemo(() => {
    if (isMyProfilePath) {
      return [...BREAD_CRUMBS_SETTINGS_PATH, ...BREAD_CRUMBS_PROFILE_PATH];
    }
    if (isIntegrationsPath) {
      return [...BREAD_CRUMBS_SETTINGS_PATH, ...BREAD_CRUMBS_INTEGRATIONS_PATH];
    }
    if (isAuthenticationPath) {
      return [
        ...BREAD_CRUMBS_SETTINGS_PATH,
        ...BREAD_CRUMBS_AUTH_SETTINGS_PATH
      ];
    }
    return [...BREAD_CRUMBS_SETTINGS_PATH, ...BREAD_CRUMBS_ACCOUNTS_PATH];
  }, [isMyProfilePath, isIntegrationsPath, isAuthenticationPath]);

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
              {user.is_admin && (
                <>
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
                  <li
                    className={classNames(styles.navItem, {
                      [styles.isActive]: isAuthenticationPath
                    })}
                  >
                    <Link to={'/settings/authentication-settings'}>
                      Auth Settings
                    </Link>
                  </li>
                </>
              )}
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
