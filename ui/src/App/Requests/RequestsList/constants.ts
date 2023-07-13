export const requestsColumns = [
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

export const SUPPORTED_REQUESTS_FILTERS = [
  'created_by',
  'repo_name',
  'pull_request_id'
];
