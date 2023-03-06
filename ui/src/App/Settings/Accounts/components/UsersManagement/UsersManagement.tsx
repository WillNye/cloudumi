import { useCallback, useEffect, useMemo, useState } from 'react';
import { Table } from 'shared/elements/Table';
import { DELETE_DATA_TYPE, userTableColumns } from '../../constants';
import UserModal from '../common/EditUserModal';
import Delete from '../common/Delete';

import css from './UsersManagement.module.css';
import { PropertyFilterProps } from '@noqdev/cloudscape';
import { extractErrorMessage } from 'core/API/utils';
import { getAllUsers } from 'core/API/settings';
import InviteUserModal from '../common/InviteUserModal/InviteUserModal';
import { User } from '../../types';

const UsersManagement = () => {
  const [allUsersData, setAllUsersData] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const [query, setQuery] = useState({
    pagination: {
      currentPageIndex: 1,
      pageSize: 10
    },
    sorting: {
      sortingColumn: {
        id: 'id',
        sortingField: 'id',
        header: 'id',
        minWidth: 180
      },
      sortingDescending: false
    },
    filtering: {
      tokens: [],
      operation: 'and'
    }
  });

  const callGetAllUsers = useCallback((query = {}) => {
    setIsLoading(true);
    setErrorMsg(null);
    getAllUsers({ filter: query })
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

  const tableRows = useMemo(() => {
    return allUsersData.map(item => {
      const canEdit = item.managed_by === 'MANUAL';
      return {
        ...item,
        email: <div>{item.email}</div>,
        delete: (
          <Delete
            canEdit={canEdit}
            dataType={DELETE_DATA_TYPE.USER}
            dataId={item.email}
            title="Delete User"
            refreshData={() => callGetAllUsers(query)}
          />
        ),
        edit: <UserModal canEdit={canEdit} user={item} />,
        groups: item.groups.length
      };
    });
  }, [allUsersData, callGetAllUsers, query]);

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
