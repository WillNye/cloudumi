import { useCallback, useEffect, useMemo, useState } from 'react';
import { Table } from 'shared/elements/Table';
import { DELETE_DATA_TYPE, userTableColumns } from '../../constants';
import UserModal from '../common/EditUserModal';
import Delete from '../common/Delete';

import { extractErrorMessage } from 'core/API/utils';
import { getAllUsers } from 'core/API/settings';
import InviteUserModal from '../common/InviteUserModal/InviteUserModal';
import { User } from '../../types';
import css from './UsersManagement.module.css';

const UsersManagement = () => {
  const [allUsersData, setAllUsersData] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pageCount, setPageCount] = useState(1);
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
        setPageCount(data.data.filtered_count);
      })
      .catch(error => {
        const errorMessage = extractErrorMessage(error);
        setErrorMsg(errorMessage);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const handleOnPageChange = useCallback(
    (newPageIndex: number) => {
      const newQuery = {
        ...query,
        pagination: {
          ...query.pagination,
          currentPageIndex: newPageIndex
        }
      };
      callGetAllUsers(newQuery);
      setQuery(newQuery);
    },
    [callGetAllUsers, query]
  );

  useEffect(
    function onQueryUpdate() {
      callGetAllUsers(query);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
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
          isLoading={isLoading}
          showPagination
          totalCount={pageCount}
          pageSize={query.pagination.pageSize}
          pageIndex={query.pagination.currentPageIndex}
          handleOnPageChange={handleOnPageChange}
        />
      </div>
    </div>
  );
};

export default UsersManagement;
