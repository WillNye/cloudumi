import { ColumnDef } from '@tanstack/react-table';

export enum ROLES_TABS {
  ELIGIBLE_ROLES = 'eligible-roles',
  ALL_ROES = 'all-roles'
}

export const ROLE_PROPERTY_SEARCH_FILTER =
  'Filter Roles by Account Name, Account ID or Role Name';

export const IAMBIC_ROLE_PROPERTY_SEARCH_FILTER =
  'Filter Roles by Resource ARN, Repository Name or File path';

export const AWS_SIGN_OUT_URL =
  'https://signin.aws.amazon.com/oauth?Action=logout';

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
    header: '',
    accessorKey: 'moreActions',
    width: '50px'
  }
];

export const allRolesColumns: ColumnDef<any, any>[] = [
  {
    header: 'Template Type',
    accessorKey: 'template_type'
  },
  {
    header: 'Resource ARN',
    accessorKey: 'secondary_resource_id'
  },
  {
    header: 'Repository Name',
    accessorKey: 'repo_name'
  },
  {
    header: 'File Path',
    accessorKey: 'file_path'
  },
  {
    header: 'Provider',
    accessorKey: 'provider'
  },
  {
    header: '',
    accessorKey: 'moreActions'
  }
];

export const SUPPORTED_FILTER_KEYS = [
  'account_name',
  'account_id',
  'role_name',
  'arn'
];
