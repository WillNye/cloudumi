import { useCallback, useEffect, useMemo, useState } from 'react';
import { Table } from 'shared/elements/Table';
import { userTableColumns } from '../../constants';
import { Button } from 'shared/elements/Button';
import UserModal from '../common/EditUserModal';
import Delete from '../common/Delete';

import css from './UsersManagement.module.css';
import { PropertyFilterProps } from '@noqdev/cloudscape';
import { extractErrorMessage } from 'core/API/utils';
import { getAllUsers } from 'core/API/settings';
import InviteUserModal from '../common/InviteUserModal/InviteUserModal';

const UsersManagement = () => {
  const [allUsersData, setAllUsersData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const [filter, setFilter] = useState<PropertyFilterProps.Query>({
    tokens: [],
    operation: 'and'
  });

  const [query, setQuery] = useState({
    pagination: {
      currentPageIndex: 1,
      pageSize: 30
    },
    sorting: {
      sorting: {
        sortingColumn: {
          id: 'id',
          sortingField: 'id',
          header: 'id',
          minWidth: 180
        },
        sortingDescending: false
      },
      sortingDescending: false
    },
    filtering: filter
  });

  const callGetAllUsers = useCallback((query = {}) => {
    setIsLoading(true);
    setErrorMsg(null);
    getAllUsers(query)
      .then(({ data }) => {
        setAllUsersData(data.data.data);
      })
      .catch(error => {
        const errorMessage = extractErrorMessage(error);
        setErrorMsg(errorMessage);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  useEffect(
    function onQueryUpdate() {
      callGetAllUsers(query);
    },
    [callGetAllUsers, query]
  );

  useEffect(() => {
    setQuery(exstingQuery => ({
      ...exstingQuery,
      filtering: filter
    }));
  }, [filter]);

  const tableRows = useMemo(() => {
    return allUsersData.map(item => {
      const canEdit = item.managed_by === 'MANUAL';
      return {
        ...item,
        email: <div>{item.email}</div>,
        delete: <Delete canEdit={canEdit} />,
        edit: <UserModal canEdit={canEdit} />
      };
    });
  }, [allUsersData]);

  return (
    <div className={css.container}>
      <div className={css.header}>
        <div>Team Members ({allUsersData.length})</div>
        <div>
          <InviteUserModal />
        </div>
      </div>
      <div className={css.table}>
        <Table
          data={tableRows}
          columns={userTableColumns}
          border="row"
          selectable
          isLoading={isLoading}
          showPagination
        />
      </div>
    </div>
  );
};

export default UsersManagement;
