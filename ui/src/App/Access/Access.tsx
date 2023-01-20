import { FC, useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';

import css from './Access.module.css';
import { ROLES_TABS } from './constants';
import EligibleRoles from './components/EligibleRoles/EligibleRoles';
import AllRoles from './components/AllRoles';
import {
  getAllRoles,
  getEligibleRoles,
  getRoleCredentials
} from 'core/API/roles';
import { extractErrorMessage } from 'core/API/utils';

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
  const [eligibleRolesData, setEligibleRolesData] = useState([]);
  const [allRolesData, setAllRolesData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(function onMount() {
    // getAllRoles().then(({ data }) => {
    //   setAllRolesData(data.data);
    // });
    // const role = {
    //   requested_role: 'arn:aws:iam::759357822767:role/noqmeter_null_test_role'
    // };
    // getRoleCredentials(role).then(({ data }) => {
    //   console.log('==========request========', data, '===========');
    // });
  }, []);

  const callGetEligibleRoles = useCallback(() => {
    setIsLoading(true);
    setErrorMsg(null);
    getEligibleRoles()
      .then(({ data }) => {
        setEligibleRolesData(data.data);
      })
      .catch(error => {
        const errorMessage = extractErrorMessage(error);
        setErrorMsg(errorMessage);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const callGetAllRoles = useCallback(() => {
    setIsLoading(true);
    setErrorMsg(null);
    getAllRoles()
      .then(({ data }) => {
        setAllRolesData(data.data);
      })
      .catch(error => {
        const errorMessage = extractErrorMessage(error);
        setErrorMsg(errorMessage);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  return (
    <div className={css.container}>
      <h3 className={css.header}>Role Access</h3>
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
        <EligibleRoles
          data={eligibleRolesData}
          getData={callGetEligibleRoles}
          isLoading={isLoading}
        />
      ) : (
        <AllRoles
          data={allRolesData}
          getData={callGetAllRoles}
          isLoading={isLoading}
        />
      )}
    </div>
  );
};
