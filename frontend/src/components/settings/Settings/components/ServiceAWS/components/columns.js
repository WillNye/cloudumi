import React from 'react'
import { Bar, RowStatusIndicator } from 'lib/Misc'

import { Button, Checkbox } from 'semantic-ui-react'

export const awsOrganizationColumns = ({ handleClick }) => [
  {
    Header: 'Organization ID',
    accessor: 'org_id',
  },
  {
    Header: 'Account ID',
    accessor: 'account_id',
  },
  {
    Header: 'Account Name',
    accessor: 'account_name',
  },
  {
    Header: 'Owner',
    accessor: 'owner',
  },
  {
    Header: 'Status',
    accessor: 'active',
    width: 60,
    align: 'center',
    Cell: ({ row }) => (
      <RowStatusIndicator isActive={row?.original?.active || true} />
    ),
  },
  {
    Header: 'Actions',
    align: 'right',
    Cell: ({ row }) => (
      <Bar>
        <Button size='mini' onClick={() => handleClick('edit', row?.original)}>
          Edit
        </Button>
        <Button
          size='mini'
          onClick={() => handleClick('remove', row?.original)}
        >
          Remove
        </Button>
      </Bar>
    ),
  },
]

export const spokeAccountsColumns = ({ handleClick }) => [
  {
    Header: 'Account Name',
    accessor: 'account_name',
    width: 80,
  },
  {
    Header: 'Account ID',
    accessor: 'account_id',
    width: 80,
  },
  {
    Header: 'Spoke Role ARN',
    accessor: 'role_arn',
  },
  {
    Header: 'Status',
    accessor: 'active',
    width: 60,
    align: 'center',
    Cell: ({ row }) => (
      <RowStatusIndicator isActive={row?.original?.active || true} />
    ),
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Bar>
        <Button size='mini' onClick={() => handleClick('edit', row?.original)}>
          Edit
        </Button>
        <Button
          size='mini'
          onClick={() => handleClick('remove', row?.original)}
        >
          Remove
        </Button>
      </Bar>
    ),
  },
]

export const hubAccountColumns = ({ handleClick }) => [
  {
    Header: 'Account Name',
    accessor: 'account_name',
    width: 80,
  },
  {
    Header: 'Account ID',
    accessor: 'account_id',
    width: 80,
  },
  {
    Header: 'Hub Role ARN',
    accessor: 'role_arn',
  },
  {
    Header: 'External ID',
    accessor: 'external_id',
    width: 60,
  },
  {
    Header: 'Status',
    accessor: 'active',
    width: 60,
    align: 'center',
    Cell: ({ row }) => (
      <RowStatusIndicator isActive={row?.original?.active || true} />
    ),
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button size='mini' onClick={() => handleClick('remove', row?.original)}>
        Remove
      </Button>
    ),
  },
]

export const roleAccessAuthColumns = ({
  handleClick = null,
  handleChange = null,
  disabled = true,
}) => [
  {
    Header: 'Tag Name',
    accessor: 'tag_name',
  },
  {
    Header: 'Source',
    accessor: 'source',
    width: 60,
    align: 'center',
  },
  {
    Header: 'Allow Web Access',
    accessor: 'web_access',
    align: 'center',
    Cell: ({ row }) => (
      <Checkbox
        toggle
        onChange={handleChange}
        disabled
        defaultChecked={row?.original?.web_access}
      />
    ),
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button
        size='mini'
        onClick={() => handleClick('remove', row?.original)}
        disabled={disabled}
      >
        Remove
      </Button>
    ),
  },
]

export const CIDRBlockColumns = ({ handleClick = null }) => [
  {
    Header: 'CIDR Block',
    Cell: ({ row }) => row?.original,
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button size='mini' onClick={() => handleClick('remove', row?.original)}>
        Remove
      </Button>
    ),
  },
]
