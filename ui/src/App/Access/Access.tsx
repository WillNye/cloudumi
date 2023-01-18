import { FC, useState } from 'react';
import { Helmet } from 'react-helmet-async';

import css from './Access.module.css';
import { ROLES_TABS } from './constants';
import EligibleRoles from './components/EligibleRoles/EligibleRoles';
import AllRoles from './components/AllRoles';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';
import { Button } from 'shared/elements/Button';

export interface AccessRole {
  arn: string;
  account_name: string;
  account_id: string;
  role_name: string;
  redirect_uri: string;
  inactive_tra: boolean;
}

export interface AccessQueryResult {
  totalCount: number;
  filteredCount: number;
  data: AccessRole[];
}

type AccessProps = AccessQueryResult;

export const Access: FC<AccessProps> = ({ data }) => {
  const [currentTab, setCurrentTab] = useState(ROLES_TABS.ELIGIBLE_ROLES);

  return (
    <div className={css.container}>
      <h3 className={css.header}>Role Access</h3>

      <Breadcrumbs
        items={[
          { name: 'Roles', url: '/' },
          { name: 'My Roles', url: '/' }
        ]}
      />
      <div>
        <nav className={css.nav}>
          <ul className={css.navList}>
            <li
              className={`${css.navItem} ${
                currentTab === ROLES_TABS.ELIGIBLE_ROLES ? css.isActive : ''
              }`}
              onClick={() => setCurrentTab(ROLES_TABS.ELIGIBLE_ROLES)}
            >
              <div className={css.text}>My Roles</div>
            </li>
            <li
              className={`${css.navItem} ${
                currentTab === ROLES_TABS.ALL_ROES ? css.isActive : ''
              }`}
              onClick={() => setCurrentTab(ROLES_TABS.ALL_ROES)}
            >
              <div className={css.text}>All Roles</div>
            </li>
          </ul>
        </nav>
      </div>
      {currentTab === ROLES_TABS.ELIGIBLE_ROLES ? (
        <EligibleRoles data={data} />
      ) : (
        <AllRoles />
      )}
    </div>
  );
};
