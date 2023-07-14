export enum REQUESTS_SECTIONS {
  MY_REQUESTS = 'my-requests',
  RECENT_REQUESTS = 'recent-requests'
}

export const myRequestsColumns = [
  {
    id: 'repo_name',
    header: 'Repo Name',
    accessorKey: 'repo_name'
  },
  {
    id: 'pull_request_id',
    header: 'Pull Request ID',
    accessorKey: 'pull_request_id'
  },
  {
    id: 'created_at',
    header: 'Created At',
    accessorKey: 'created_at'
  },
  {
    id: 'created_by',
    header: 'Created By',
    accessorKey: 'created_by'
  },
  { id: 'status', header: 'Status', accessorKey: 'status' }
];
