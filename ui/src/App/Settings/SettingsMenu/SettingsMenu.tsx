import { FC } from 'react';
import { Link } from 'react-router-dom';
import appConfigImg from '../../../assets/vendor/app-config.svg';
import styles from './SettingsMenu.module.css';

const SettingsMenu: FC = () => (
  <div className={styles.container}>
    <div className={styles.header}>Account Settings</div>
    <p className={styles.description}>
      Manage and customize all aspects of your account and system integrations.
    </p>
    <div className={styles.card}>
      <img src={appConfigImg} />
      <div>
        <div className={styles.subHeader}>
          <Link to="/settings/integrations">
            Integrations and Connected Apps
          </Link>
        </div>
        <p>
          Set up Single Sign-On (SSO) and System for Cross-domain Identity
          Management (SCIM) integrations, receive notifications, and connect
          with cloud providers for secure and streamlined operations.
        </p>
      </div>
    </div>
    <div className={styles.card}>
      <img src={appConfigImg} />

      <div>
        <div className={styles.subHeader}>
          <Link to="/settings/profile">Personal Settings</Link>
        </div>
        <p>
          Manage and customize your personal account information. Update your
          profile details, change your password, set notifications preferences,
          and and manage your privacy preferences.
        </p>
      </div>
    </div>
    <div className={styles.card}>
      <img src={appConfigImg} />

      <div>
        <div className={styles.subHeader}>
          <Link to="/settings/accounts">Accounts Management</Link>
        </div>
        <p>
          View Accounts Management Settings to manage users and groups. Add new
          accounts, edit existing ones, and assign specific groups to each user.
        </p>
      </div>
    </div>
  </div>
);

export default SettingsMenu;
