import { useCallback, useMemo, useState } from 'react';
import { Table } from 'shared/elements/Table';
import { DELETE_DATA_TYPE, userTableColumns } from '../../constants';
import UserModal from '../common/EditUserModal';
import Delete from '../common/Delete';

import { getAllUsers } from 'core/API/settings';
import InviteUserModal from '../common/InviteUserModal';
import { useQuery } from '@tanstack/react-query';
import css from './UsersManagement.module.css';

const UsersManagement = () => {
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

  const {
    refetch: callGetAllUsers,
    isLoading,
    data
  } = useQuery({
    queryFn: getAllUsers,
    queryKey: ['allUsers', { filter: query }]
  });

  const allUsersData = useMemo(() => {
    return data?.data;
  }, [data]);

  const handleOnPageChange = useCallback((newPageIndex: number) => {
    setQuery(query => ({
      ...query,
      pagination: {
        ...query.pagination,
        currentPageIndex: newPageIndex
      }
    }));
  }, []);

  const tableRows = useMemo(() => {
    return (allUsersData?.data || []).map(item => {
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
            refreshData={callGetAllUsers}
          />
        ),
        edit: <UserModal canEdit={canEdit} user={item} />,
        groups: item.groups.length
      };
    });
  }, [allUsersData, callGetAllUsers]);

  return (
    <div className={css.container}>
      <div className={css.header}>
        <div>Team Members ({allUsersData?.filtered_count})</div>
        <div>
          <InviteUserModal refreshData={callGetAllUsers} />
        </div>
      </div>
      <div className={css.table}>
        <Table
          data={tableRows}
          columns={userTableColumns}
          border="row"
          isLoading={isLoading}
          showPagination
          totalCount={allUsersData?.filtered_count || query.pagination.pageSize}
          pageSize={query.pagination.pageSize}
          pageIndex={query.pagination.currentPageIndex}
          handleOnPageChange={handleOnPageChange}
        />
      </div>
    </div>
  );
};

export default UsersManagement;
