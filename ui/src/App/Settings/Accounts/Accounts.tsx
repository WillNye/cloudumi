import { FC, useEffect, useMemo, useState } from 'react';
import css from './Accounts.module.css';
import { ACCOUNT_SETTINGS_TABS } from './constants';
import Groups from './components/GroupsManagement';
import Users from './components/UsersManagement';
import { PropertyFilterProps } from '@noqdev/cloudscape';

export const AccountSettings: FC = () => {
  const [currentTab, setCurrentTab] = useState<ACCOUNT_SETTINGS_TABS>(
    ACCOUNT_SETTINGS_TABS.USERS
  );

  const content = useMemo(() => {
    if (currentTab === ACCOUNT_SETTINGS_TABS.GROUPS) {
      return <Groups />;
    }

    return <Users />;
  }, [currentTab]);

  return (
    <div className={css.container}>
      <br />
      <div>
        <nav className={css.nav}>
          <ul className={css.navList}>
            <li
              className={`${css.navItem} ${
                currentTab === ACCOUNT_SETTINGS_TABS.USERS && css.isActive
              }`}
              onClick={() => setCurrentTab(ACCOUNT_SETTINGS_TABS.USERS)}
            >
              <div className={css.text}>User Management</div>
            </li>
            <li
              className={`${css.navItem} ${
                currentTab === ACCOUNT_SETTINGS_TABS.GROUPS && css.isActive
              }`}
              onClick={() => setCurrentTab(ACCOUNT_SETTINGS_TABS.GROUPS)}
            >
              <div className={css.text}>Group Management</div>
            </li>
          </ul>
        </nav>
      </div>
      {content}
    </div>
  );
};

export default AccountSettings;
