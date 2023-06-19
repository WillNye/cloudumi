import { ColumnDef } from '@tanstack/react-table';

export const eligibleRolesColumns = [
  {
    header: 'AWS Console Sign-In',
    accessorKey: 'arn',
    id: 'arn',
    width: '220px',
    sortable: false
  },
  {
    header: 'Account Details',
    accessorKey: 'name',
    sortable: true
  },
  {
    header: 'Role Name',
    accessorKey: 'roleName',
    sortable: true
  },
  {
    header: 'View Details',
    accessorKey: 'viewDetails',
    width: '50px',
    sortable: false
  },
  {
    header: 'More Actions',
    accessorKey: 'moreActions',
    width: '50px',
    sortable: false
  }
];

export const allRolesColumns: ColumnDef<any, any>[] = [
  {
    header: 'Account Details',
    accessorKey: 'name',
    id: 'name',
    footer: props => props.column.id
    // sortable: true
  },
  {
    header: 'Role Name',
    accessorKey: 'roleName',
    id: 'roleName',
    // sortable: true,
    footer: props => props.column.id
  },
  {
    header: 'More Actions',
    accessorKey: 'moreActions',
    id: 'moreActions',
    // width: '50px',
    // sortable: false,
    footer: props => props.column.id
  }
];

export const SUPPORTED_FILTER_KEYS = [
  'account_name',
  'account_id',
  'role_name'
];
