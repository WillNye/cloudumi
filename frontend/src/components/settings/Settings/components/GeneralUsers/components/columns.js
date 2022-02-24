import React from 'react'
import { RowStatusIndicator } from 'lib/Misc'

import { Button } from 'semantic-ui-react'

export const userColumns = ({ handleClick }) => [
  {
    Header: 'User',
    accessor: 'user',
  },
  {
    Header: 'Email',
    accessor: 'email',
  },
  {
    Header: 'Updated at',
    accessor: 'updatedAt',
  },
  {
    Header: 'Created at',
    accessor: 'createdAt',
  },
  {
    Header: 'Expires',
    accessor: 'expiration',
  },
  {
    Header: 'Enabled',
    accessor: 'enabled',
    width: 60,
    align: 'center',
    Cell: ({ row }) => <RowStatusIndicator isActive={row?.values?.active} />,
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button size='mini' onClick={() => handleClick('remove', row?.values)}>
        Remove
      </Button>
    ),
  },
]

export const groupColumns = ({ handleClick }) => [
  {
    Header: 'Group Name',
    accessor: 'name',
  },
  {
    Header: 'Description',
    accessor: 'description',
  },
  {
    Header: 'Updated at',
    accessor: 'updatedAt',
  },
  {
    Header: 'Created at',
    accessor: 'createdAt',
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button size='mini' onClick={() => handleClick('remove', row?.values)}>
        Remove
      </Button>
    ),
  },
]
