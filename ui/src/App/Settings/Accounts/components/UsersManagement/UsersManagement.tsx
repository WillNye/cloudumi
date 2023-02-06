import { useMemo } from 'react';
import { Table } from 'shared/elements/Table';
import { usersMockData } from '../../mockData';
import { userTableColumns } from '../../constants';
import { Button } from 'shared/elements/Button';
import UserModal from '../common/UserModal';
import Delete from '../common/Delete';

import css from './UsersManagement.module.css';

const UsersManagement = () => {
  const tableRows = useMemo(() => {
    return usersMockData.map(item => {
      return {
        ...item,
        email: <div>{item.email}</div>,
        delete: <Delete />,
        edit: <UserModal />
      };
    });
  }, []);

  return (
    <div className={css.container}>
      <div className={css.header}>
        <div>Team Members ({usersMockData.length})</div>
        <Button>Invite Member</Button>
      </div>
      <div className={css.table}>
        <Table data={tableRows} columns={userTableColumns} border="row" />
      </div>
    </div>
  );
};

export default UsersManagement;
