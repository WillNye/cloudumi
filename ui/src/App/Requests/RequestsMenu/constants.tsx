export enum REQUESTS_SECTIONS {
  MY_REQUESTS = 'my-requests',
  RECENT_REQUESTS = 'recent-requests'
}

export const recentRequestsColumns = [
  {
    Header: 'User',
    accessor: 'user',
    sortable: true
  },
  {
    Header: 'Request ID',
    accessor: 'requestId',
    sortable: true
  },
  {
    Header: 'ARN',
    accessor: 'arn',
    sortable: false
  },
  {
    Header: 'Created At',
    accessor: 'createdAt',
    sortable: false
  }
];

export const myRequestsColumns = [
  {
    Header: 'User',
    accessor: 'user',
    sortable: true
  },
  {
    Header: 'Request ID',
    accessor: 'requestId',
    sortable: true
  },
  {
    Header: 'ARN',
    accessor: 'arn',
    sortable: false
  },
  {
    Header: 'Created At',
    accessor: 'createdAt',
    sortable: false
  }
];
