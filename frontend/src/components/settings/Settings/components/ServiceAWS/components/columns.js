import React from 'react'
import { RowStatusIndicator } from 'lib/Misc'

import { Button, Checkbox } from 'semantic-ui-react'

export const awsOrganizationColumns = ({ handleClick }) => [{
  Header: 'Organization ID',
  accessor: 'org_id'
}, {
  Header: 'Account ID',
  accessor: 'account_id'
}, {
  Header: 'Account Name',
  accessor: 'account_name'
}, {
  Header: 'Owner',
  accessor: 'owner'
}, {
  Header: 'Status',
  accessor: 'active',
  width: 60,
  align: 'center',
  Cell: ({ row }) => (
    <RowStatusIndicator isActive={row?.values?.active || true} />
  )
}, {
  Header: 'Actions',
  width: 80,
  align: 'right',
  Cell: ({ row }) => (
    <Button size="mini" onClick={() => handleClick('remove', row?.values)}>
      Remove
    </Button>
  )
}];

export const spokeAccountsColumns = ({ handleClick }) => [{
  Header: 'Account Name',
  accessor: 'name',
  width: 80
}, {
  Header: 'Account ID',
  accessor: 'account_id',
  width: 80
}, {
  Header: 'Hub Role ARN',
  accessor: 'role_arn'
}, {
  Header: 'External ID',
  accessor: 'external_id',
  width: 60
}, {
  Header: 'Status',
  accessor: 'active',
  width: 60,
  align: 'center',
  Cell: ({ row }) => (
    <RowStatusIndicator isActive={row?.values?.active || true} />
  )
}, {
  Header: 'Actions',
  width: 80,
  align: 'right',
  Cell: ({ row }) => (
    <Button size="mini" onClick={() => handleClick('remove', row?.values)}>
      Remove
    </Button>
  )
}];

export const hubAccountColumns = ({ handleClick }) => [{
  Header: 'Account Name',
  accessor: 'name',
  width: 80
}, {
  Header: 'Account ID',
  accessor: 'account_id',
  width: 80
}, {
  Header: 'Hub Role ARN',
  accessor: 'role_arn'
}, {
  Header: 'External ID',
  accessor: 'external_id',
  width: 60
}, {
  Header: 'Status',
  accessor: 'active',
  width: 60,
  align: 'center',
  Cell: ({ row }) => (
    <RowStatusIndicator isActive={row?.values?.active || true} />
  )
}, {
  Header: 'Actions',
  width: 80,
  align: 'right',
  Cell: ({ row }) => (
    <Button size="mini" onClick={() => handleClick('remove', row?.values)}>
      Remove
    </Button>
  )
}];

export const roleAccessAuthColumns = ({
  handleClick = null,
  handleChange = null,
  disabled,
}) => [
  {
    Header: 'Tag Name',
    accessor: 'tagName',
  },
  {
    Header: 'Authorizations',
    accessor: 'authorizations',
    width: 60,
    align: 'center',
  },
  {
    Header: 'Allow Web Console Access',
    accessor: 'allowWebConsole',
    align: 'right',
    Cell: ({ row }) => (
      <Checkbox
        toggle
        onChange={handleChange}
        disabled={disabled}
        defaultChecked={row?.values?.allowWebConsole}
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
        onClick={() => handleClick('remove', row?.values)}
        disabled={disabled}
      >
        Remove
      </Button>
    ),
  },
]
