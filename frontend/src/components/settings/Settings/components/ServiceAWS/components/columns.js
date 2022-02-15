import React from 'react';
import { RowStatusIndicator } from '../../../../../../lib/Misc';

import { Button, Checkbox } from 'semantic-ui-react';

export const awsOrganizationColumns = ({ handleClick }) => [{
  Header: 'Organization ID',
  accessor: 'organizationId'
}, {
  Header: 'Account ID',
  accessor: 'accountId'
}, {
  Header: 'Account Name',
  accessor: 'accountName'
}, {
  Header: 'Owner',
  accessor: 'owner'
}, {
  Header: 'Status',
  accessor: 'active',
  width: 60,
  align: 'center',
  Cell: ({ row }) => (
    <RowStatusIndicator isActive={row?.values?.active} />
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
  accessor: 'accountName'
}, {
  Header: 'Account ID',
  accessor: 'accountId'
}, {
  Header: 'Role',
  accessor: 'role'
}, {
  Header: 'Account Admin',
  accessor: 'accountAdmin'
}, {
  Header: 'Status',
  accessor: 'active',
  width: 60,
  align: 'center',
  Cell: ({ row }) => (
    <RowStatusIndicator isActive={row?.values?.active} />
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
  accessor: 'accountName'
}, {
  Header: 'Account ID',
  accessor: 'accountId',
  width: 80
}, {
  Header: 'Role',
  accessor: 'role',
  width: 80
}, {
  Header: 'External ID',
  accessor: 'externalId'
}, {
  Header: 'Status',
  accessor: 'active',
  width: 60,
  align: 'center',
  Cell: ({ row }) => (
    <RowStatusIndicator isActive={row?.values?.active} />
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

export const roleAccessAuthColumns = ({ handleClick, handleChange }) => [{
  Header: 'Tag Name',
  accessor: 'tagName'
}, {
  Header: 'Authorizations',
  accessor: 'authorizations',
  width: 60,
  align: 'center'
}, {
  Header: 'Allow Web Console Access',
  accessor: 'allowWebConsole',
  align: 'right',
  Cell: ({ row }) => (
    <Checkbox toggle onChange={handleChange} defaultChecked={row?.values?.allowWebConsole} />
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