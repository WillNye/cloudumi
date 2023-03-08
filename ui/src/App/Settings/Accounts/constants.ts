export enum ACCOUNT_SETTINGS_TABS {
  USERS = 'USERS',
  GROUPS = 'GROUPS'
}

export enum DELETE_DATA_TYPE {
  USER = 'user',
  GROUP = 'group'
}

export enum UPDATE_USER_ACTIONS {
  RESET_PASSWORD = 'reset_password',
  RESET_MFA = 'reset_mfa',
  UPDATE_USER = 'update_user'
}

export const userTableColumns = [
  {
    Header: 'Email',
    accessor: 'email',
    sortable: true
  },
  {
    Header: 'Status',
    accessor: 'status'
  },
  {
    Header: 'Managed By',
    accessor: 'managed_by'
  },
  {
    Header: 'Groups',
    accessor: 'groups'
  },
  {
    accessor: 'edit',
    width: '50px'
  },
  {
    accessor: 'delete',
    width: '50px'
  }
];

export const groupsTableColumns = [
  {
    Header: 'Name',
    accessor: 'name',
    sortable: true
  },
  {
    Header: 'Description',
    accessor: 'description'
  },
  {
    Header: 'Managed By',
    accessor: 'managed_by'
  },
  {
    Header: 'Users',
    accessor: 'users'
  },
  {
    accessor: 'edit',
    width: '50px'
  },
  {
    accessor: 'delete',
    width: '50px'
  }
];
