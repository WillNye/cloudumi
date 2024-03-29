import { useCallback, useMemo, useState } from 'react';

import { Table } from 'shared/elements/Table';

import { DELETE_DATA_TYPE, groupsTableColumns } from '../../constants';

import css from './GroupsManagement.module.css';
import Delete from '../common/Delete';
import GroupsModal from '../common/EditGroupsModal';
import { getAdminGroups, getAllGroups } from 'core/API/settings';
import AddGroupModal from '../common/AddGroupModal/AddGroupModal';
import { useQuery } from '@tanstack/react-query';
import EditAdminGroupsModal from '../common/EditAdminGroupsModal';

const GroupsManagement = () => {
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
    refetch: callGetAllGroups,
    isLoading,
    data
  } = useQuery({
    queryFn: getAllGroups,
    queryKey: ['allGroups', { filter: query }]
  });

  const allGroupsData = useMemo(() => data?.data, [data]);

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
    return (allGroupsData?.data || []).map(item => {
      return {
        ...item,
        name: <div>{item.name}</div>,
        delete: (
          <Delete
            dataType={DELETE_DATA_TYPE.GROUP}
            dataId={item.name}
            title="Delete Group"
          />
        ),
        edit: <GroupsModal group={item} />,
        users: item.users.length
      };
    });
  }, [allGroupsData]);

  return (
    <div className={css.container}>
      <div className={css.header}>
        <div>Groups ({allGroupsData?.filtered_count})</div>
        <div className={css.buttons}>
          <EditAdminGroupsModal />
          <AddGroupModal refreshData={callGetAllGroups} />
        </div>
      </div>
      <div className={css.table}>
        <Table
          data={tableRows}
          columns={groupsTableColumns}
          border="row"
          isLoading={isLoading}
          totalCount={
            allGroupsData?.filtered_count || query.pagination.pageSize
          }
          pageSize={query.pagination.pageSize}
          pageIndex={query.pagination.currentPageIndex}
          handleOnPageChange={handleOnPageChange}
          showPagination
        />
      </div>
    </div>
  );
};

export default GroupsManagement;
