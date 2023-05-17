import { FC, useMemo, useState } from 'react';
import { ACCOUNT_SETTINGS_TABS } from './constants';
import Groups from './components/GroupsManagement';
import Users from './components/UsersManagement';
import css from './Accounts.module.css';
import { LineBreak } from 'shared/elements/LineBreak';

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
      <LineBreak />
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
