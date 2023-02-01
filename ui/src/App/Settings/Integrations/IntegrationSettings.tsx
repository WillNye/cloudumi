import { Button } from 'shared/elements/Button';
import styles from './IntegrationSettings.module.css';
import { INTEGRATIONS_TABS } from './constants';
import { useMemo, useState } from 'react';
import NotificationSettings from './NotificationSettings';
import AuthenticationSettings from './AuthenticationSettings';
import CloudProviderSettings from './CloudProviderSettings';

const IntegrationSettings = () => {
  const [currentTab, setCurrentTab] = useState<INTEGRATIONS_TABS>(
    INTEGRATIONS_TABS.AUTHENTICATION
  );

  const content = useMemo(() => {
    if (currentTab === INTEGRATIONS_TABS.AUTHENTICATION) {
      return <AuthenticationSettings />;
    }

    if (currentTab === INTEGRATIONS_TABS.CLOUD_PROVIDER) {
      return <CloudProviderSettings />;
    }

    return <NotificationSettings />;
  }, [currentTab]);

  return (
    <div className={styles.container}>
      <div className={styles.menu}>
        <Button color="secondary">Authentication</Button>
        <Button color="secondary" variant="text">
          Cloud Provider
        </Button>
        <Button color="secondary" variant="text">
          Authentication
        </Button>
      </div>

      <div>
        <nav className={styles.nav}>
          <ul className={styles.navList}>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.AUTHENTICATION
                  ? styles.isActive
                  : ''
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.AUTHENTICATION)}
            >
              <div className={styles.text}>Authentication</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.CLOUD_PROVIDER
                  ? styles.isActive
                  : ''
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.CLOUD_PROVIDER)}
            >
              <div className={styles.text}>Cloud Providers</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.NOTIFICATIONS
                  ? styles.isActive
                  : ''
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.NOTIFICATIONS)}
            >
              <div className={styles.text}>Notifications</div>
            </li>
          </ul>
        </nav>
      </div>
      <div>{content}</div>
    </div>
  );
};

export default IntegrationSettings;
