import { ColumnDef } from '@tanstack/react-table';

export const eligibleRolesColumns = [
  {
    header: 'AWS Console Sign-In',
    accessorKey: 'arn',
    id: 'arn',
    width: '220px'
  },
  {
    header: 'Account Details',
    accessorKey: 'name'
  },
  {
    header: 'Role Name',
    accessorKey: 'roleName'
  },
  {
    header: 'View Details',
    accessorKey: 'viewDetails',
    width: '50px'
  },
  {
    header: 'More Actions',
    accessorKey: 'moreActions',
    width: '50px'
  }
];

export const allRolesColumns: ColumnDef<any, any>[] = [
  {
    header: 'Account Details',
    accessorKey: 'name',
    id: 'name',
    footer: props => props.column.id
  },
  {
    header: 'Role Name',
    accessorKey: 'roleName',
    id: 'roleName',
    footer: props => props.column.id
  },
  {
    header: 'More Actions',
    accessorKey: 'moreActions',
    id: 'moreActions',
    footer: props => props.column.id
  }
];

export const SUPPORTED_FILTER_KEYS = [
  'account_name',
  'account_id',
  'role_name',
  'arn'
];
