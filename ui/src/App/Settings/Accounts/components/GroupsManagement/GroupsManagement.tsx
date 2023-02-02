import { useMemo } from 'react';

import { Table } from 'shared/elements/Table';

import { groupsMockData } from '../../mockData';
import { groupsTableColumns } from '../../constants';

import css from './GroupsManagement.module.css';

const GroupsManagement = () => {
  const tableRows = useMemo(() => {
    return groupsMockData.map(item => {
      return {
        ...item,
        name: <div>{item.name}</div>
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
