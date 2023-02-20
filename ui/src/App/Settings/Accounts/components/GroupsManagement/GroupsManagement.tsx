import { useCallback, useEffect, useMemo, useState } from 'react';

import { Table } from 'shared/elements/Table';

import { groupsTableColumns } from '../../constants';

import css from './GroupsManagement.module.css';
import Delete from '../common/Delete';
import GroupsModal from '../common/EditGroupsModal';
import { Button } from 'shared/elements/Button';
import { extractErrorMessage } from 'core/API/utils';
import { PropertyFilterProps } from '@noqdev/cloudscape/property-filter';
import { getAllGroups } from 'core/API/settings';
import AddGroupModal from '../common/AddGroupModal/AddGroupModal';

const GroupsManagement = () => {
  const [allGroupsData, setAllGroupsData] = useState([]);
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
    getAllGroups(query)
      .then(({ data }) => {
        setAllGroupsData(data.data.data);
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
    return allGroupsData.map(item => {
      const canEdit = item.managed_by === 'MANUAL';

      return {
        ...item,
        name: <div>{item.name}</div>,
        delete: <Delete canEdit={canEdit} />,
        edit: <GroupsModal canEdit={canEdit} />,
        users: item.users.map((group, index) => <div key={index}>{group}</div>)
      };
    });
  }, [allGroupsData]);

  return (
    <div className={css.container}>
      <div className={css.header}>
        <div>Groups ({allGroupsData.length})</div>
        <AddGroupModal />
      </div>
      <div className={css.table}>
        <Table
          data={tableRows}
          columns={groupsTableColumns}
          border="row"
          selectable
          isLoading={isLoading}
          showPagination
        />
      </div>
    </div>
  );
};

export default GroupsManagement;
