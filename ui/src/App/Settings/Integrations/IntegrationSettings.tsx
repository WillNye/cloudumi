import styles from './IntegrationSettings.module.css';
import { INTEGRATIONS_TABS } from './constants';
import { useMemo, useState } from 'react';
import NotificationSettings from './components/NotificationSettings';
import AuthenticationSettings from './components/AuthenticationSettings';
import CloudProviderSettings from './components/CloudProviderSettings';
import IambicSettings from './components/IambicSettings';

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

    if (currentTab === INTEGRATIONS_TABS.IAMBIC) {
      return <IambicSettings />;
    }

    return <NotificationSettings />;
  }, [currentTab]);

  return (
    <div className={styles.container}>
      <p>
        Set up Single Sign-On (SSO) and System for Cross-domain Identity
        Management (SCIM) integrations, receive notifications, and connect with
        cloud providers for secure and streamlined operations.
      </p>
      <br />

      <div>
        <nav className={styles.nav}>
          <ul className={styles.navList}>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.AUTHENTICATION &&
                styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.AUTHENTICATION)}
            >
              <div className={styles.text}>Authentication</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.CLOUD_PROVIDER &&
                styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.CLOUD_PROVIDER)}
            >
              <div className={styles.text}>Cloud Providers</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.NOTIFICATIONS &&
                styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.NOTIFICATIONS)}
            >
              <div className={styles.text}>Notifications</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === INTEGRATIONS_TABS.IAMBIC && styles.isActive
              }`}
              onClick={() => setCurrentTab(INTEGRATIONS_TABS.IAMBIC)}
            >
              <div className={styles.text}>Iambic</div>
            </li>
          </ul>
        </nav>
      </div>
      <div className={styles.content}>{content}</div>
    </div>
  );
};

export default IntegrationSettings;
