import { FC, useMemo, useState } from 'react';
import { PROFILE_SETTINGS_TABS } from './constants';
import ChangePassword from './components/ChangePassword';
import UserDetails from './components/UserDetails';
import css from './ProfileSettings.module.css';

export const ProfileSettings: FC = () => {
  const [currentTab, setCurrentTab] = useState<PROFILE_SETTINGS_TABS>(
    PROFILE_SETTINGS_TABS.DETAILS
  );

  const content = useMemo(() => {
    if (currentTab === PROFILE_SETTINGS_TABS.CHANGE_PASSWORD) {
      return <ChangePassword />;
    }

    return <UserDetails />;
  }, [currentTab]);

  return (
    <div className={css.container}>
      <p>
        Manage and customize your personal account information. Update your
        profile details, change your password, set notifications preferences,
        and and manage your privacy preferences.
      </p>
      <br />
      <div>
        <nav className={css.nav}>
          <ul className={css.navList}>
            <li
              className={`${css.navItem} ${
                currentTab === PROFILE_SETTINGS_TABS.DETAILS && css.isActive
              }`}
              onClick={() => setCurrentTab(PROFILE_SETTINGS_TABS.DETAILS)}
            >
              <div className={css.text}>User Details</div>
            </li>
            <li
              className={`${css.navItem} ${
                currentTab === PROFILE_SETTINGS_TABS.CHANGE_PASSWORD &&
                css.isActive
              }`}
              onClick={() =>
                setCurrentTab(PROFILE_SETTINGS_TABS.CHANGE_PASSWORD)
              }
            >
              <div className={css.text}>Change Password</div>
            </li>
          </ul>
        </nav>
      </div>
      {content}
    </div>
  );
};

export default ProfileSettings;
