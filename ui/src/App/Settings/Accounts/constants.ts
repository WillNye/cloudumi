export const userTableColumns = [
  {
    Header: 'Email',
    accessor: 'email',
    sortable: true
  },
  {
    Header: 'Groups',
    accessor: 'groups'
  },
  {
    accessor: 'edit',
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
    Header: 'Users',
    accessor: 'users'
  },
  {
    accessor: 'edit',
    width: '50px'
  }
];
