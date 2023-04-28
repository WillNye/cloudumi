export const AWSOrganizationCoulumns = [
  {
    Header: 'Organization ID',
    accessor: 'org_id'
  },
  {
    Header: 'Account ID',
    accessor: 'account_id'
  },
  {
    Header: 'Account Name',
    accessor: 'account_name'
  },
  {
    Header: 'Owner',
    accessor: 'owner'
  },
  {
    Header: 'Status',
    accessor: 'status'
  },
  {
    Header: 'Actions',
    accessor: 'actions'
  }
];

export const AWS_ORGANIZATION_DELETE_MESSAGE =
  // eslint-disable-next-line max-len
  'Are you sure you want to delete this item? This action cannot be undone and all associated data will be permanently removed.';
