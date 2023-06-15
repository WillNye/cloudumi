export enum REQUESTS_SECTIONS {
  MY_REQUESTS = 'my-requests',
  RECENT_REQUESTS = 'recent-requests'
}

export const recentRequestsColumns = [
  {
    header: 'User',
    accessorKey: 'user',
    sortable: true
  },
  {
    header: 'Request ID',
    accessorKey: 'requestId',
    sortable: true
  },
  {
    header: 'ARN',
    accessorKey: 'arn',
    sortable: false
  },
  {
    header: 'Created At',
    accessorKey: 'createdAt',
    sortable: false
  }
];

export const myRequestsColumns = [
  {
    header: 'User',
    accessorKey: 'user',
    sortable: true
  },
  {
    header: 'Request ID',
    accessorKey: 'requestId',
    sortable: true
  },
  {
    header: 'ARN',
    accessorKey: 'arn',
    sortable: false
  },
  {
    header: 'Created At',
    accessorKey: 'createdAt',
    sortable: false
  }
];
