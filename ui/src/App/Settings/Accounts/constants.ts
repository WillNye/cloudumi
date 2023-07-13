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
    header: 'Email',
    accessorKey: 'email'
  },
  {
    header: 'Status',
    accessorKey: 'status'
  },
  {
    header: 'Managed By',
    accessorKey: 'managed_by'
  },
  {
    header: 'Groups',
    accessorKey: 'groups'
  },
  {
    header: '',
    accessorKey: 'edit',
    width: '50px'
  },
  {
    header: '',
    accessorKey: 'delete',
    width: '50px'
  }
];

export const groupsTableColumns = [
  {
    header: 'Name',
    accessorKey: 'name'
  },
  {
    header: 'Description',
    accessorKey: 'description'
  },
  {
    header: 'Managed By',
    accessorKey: 'managed_by'
  },
  {
    header: 'Users',
    accessorKey: 'users'
  },
  {
    header: '',
    accessorKey: 'edit',
    width: '50px'
  },
  {
    header: '',
    accessorKey: 'delete',
    width: '50px'
  }
];
