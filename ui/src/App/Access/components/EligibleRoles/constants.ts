export const eligibleRolesColumns = [
  {
    Header: 'AWS Console Sign-In',
    accessor: 'arn',
    width: '220px',
    sortable: false
  },
  {
    Header: 'Account Details',
    accessor: 'name',
    sortable: true
  },
  {
    Header: 'Role Name',
    accessor: 'roleName',
    sortable: true
  },
  {
    accessor: 'viewDetails',
    width: '50px',
    sortable: false
  },
  {
    accessor: 'moreActions',
    width: '50px',
    sortable: false
  }
];

export const allRolesColumns = [
  {
    Header: 'Account Details',
    accessor: 'name',
    sortable: true
  },
  {
    Header: 'Role Name',
    accessor: 'roleName',
    sortable: true
  },
  {
    accessor: 'moreActions',
    width: '50px',
    sortable: false
  }
];
