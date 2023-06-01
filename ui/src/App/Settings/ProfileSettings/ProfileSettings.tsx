import { FC, useMemo, useState } from 'react';
import { PROFILE_SETTINGS_TABS } from './constants';
import ChangePassword from './components/ChangePassword';
import UserDetails from './components/UserDetails';
import css from './ProfileSettings.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { AWS_REGIONS } from 'core/API/constants';
import { Select, SelectOption } from 'shared/form/Select';

export const ProfileSettings: FC = () => {
  const [currentTab, setCurrentTab] = useState<PROFILE_SETTINGS_TABS>(
    PROFILE_SETTINGS_TABS.DETAILS
  );

  const userStoredPreferences = JSON.parse(
    localStorage.getItem('user-preferences') || '{}'
  );
  const [region, setRegion] = useState(
    userStoredPreferences.access?.aws?.default_region || ''
  );

  const handleRegionChange = selectedRegion => {
    setRegion(selectedRegion);
    localStorage.setItem(
      'user-preferences',
      JSON.stringify({
        ...userStoredPreferences,
        access: {
          aws: {
            default_region: selectedRegion
          }
        }
      })
    );
  };

  const content = useMemo(() => {
    if (currentTab === PROFILE_SETTINGS_TABS.CHANGE_PASSWORD) {
      return <ChangePassword />;
    } else if (currentTab === PROFILE_SETTINGS_TABS.ACCESS_PREFERENCES) {
      return (
        <div>
          <LineBreak />
          <h3>Default Region for AWS Console Access</h3>
          <LineBreak />
          <p>
            Select the default region to use when logging in to the AWS Console.
            This can be overridden on a per-role basis.
          </p>
          <LineBreak />
          <Select id="region" value={region} onChange={handleRegionChange}>
            {AWS_REGIONS.map(region => (
              <SelectOption key={region} value={region}>
                {region}
              </SelectOption>
            ))}
          </Select>
        </div>
      );
    }

    return <UserDetails />;
  }, [currentTab, region]);

  return (
    <div className={css.container}>
      <p>
        Manage and customize your personal account information. Update your
        profile details, change your password, set notifications preferences,
        and and manage your privacy preferences.
      </p>
      <LineBreak />
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
            <li
              className={`${css.navItem} ${
                currentTab === PROFILE_SETTINGS_TABS.ACCESS_PREFERENCES &&
                css.isActive
              }`}
              onClick={() =>
                setCurrentTab(PROFILE_SETTINGS_TABS.ACCESS_PREFERENCES)
              }
            >
              <div className={css.text}>Access Preferences</div>
            </li>
          </ul>
        </nav>
      </div>
      {content}
    </div>
  );
};

export default ProfileSettings;
