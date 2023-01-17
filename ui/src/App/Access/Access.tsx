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
      <br />
      <h3>Role Access</h3>
      <br />

      <Breadcrumbs
        items={[
          { name: 'Roles', url: '/' },
          { name: 'My Roles', url: '/' }
        ]}
      />
      <br />
      <br />
      <div>
        <Button
          onClick={() => setCurrentTab(ROLES_TABS.ELIGIBLE_ROLES)}
          fullWidth
        >
          My Roles
        </Button>
        <Button onClick={() => setCurrentTab(ROLES_TABS.ALL_ROES)} fullWidth>
          All Roles
        </Button>
      </div>

      <br />
      <br />
      {currentTab === ROLES_TABS.ELIGIBLE_ROLES ? (
        <EligibleRoles data={data} />
      ) : (
        <AllRoles />
      )}
    </div>
  );
};
