import { useMemo } from 'react';

import { Table } from 'shared/elements/Table';

import { groupsMockData } from '../../mockData';
import { groupsTableColumns } from '../../constants';

import css from './GroupsManagement.module.css';
import Delete from '../common/Delete';
import GroupsModal from '../common/GroupsModal';

const GroupsManagement = () => {
  const tableRows = useMemo(() => {
    return groupsMockData.map(item => {
      return {
        ...item,
        name: <div>{item.name}</div>,
        delete: <Delete />,
        edit: <GroupsModal />
      };
    });
  }, []);

  return (
    <div className={css.container}>
      <div className={css.table}>
        <Table data={tableRows} columns={groupsTableColumns} border="row" />
      </div>
    </div>
  );
};

export default GroupsManagement;
