import { useMemo } from 'react';

import { Table } from 'shared/elements/Table';

import { usersMockData } from '../../mockData';
import { userTableColumns } from '../../constants';

import css from './UsersManagement.module.css';

const UsersManagement = () => {
  const tableRows = useMemo(() => {
    return usersMockData.map(item => {
      return {
        ...item,
        email: <div>{item.email}</div>
      };
    });
  }, []);

  return (
    <div className={css.container}>
      <div className={css.table}>
        <Table data={tableRows} columns={userTableColumns} border="row" />
      </div>
    </div>
  );
};

export default UsersManagement;
