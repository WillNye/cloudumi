export const requestsColumns = [
  {
    id: 'repo_name',
    header: 'Repo Name',
    accessorKey: 'repo_name',
    sortable: true
  },
  {
    id: 'pull_request_id',
    header: 'Pull Request ID',
    accessorKey: 'pull_request_id',
    sortable: true
  },
  {
    id: 'created_at',
    header: 'Created At',
    accessorKey: 'created_at',
    sortable: true
  },
  {
    id: 'created_by',
    header: 'Created By',
    accessorKey: 'created_by',
    sortable: true
  },
  { id: 'status', header: 'Status', accessorKey: 'status', sortable: true }
];

export const SUPPORTED_REQUESTS_FILTERS = [
  'created_by',
  'repo_name',
  'pull_request_id'
];
