import React from 'react'

import { Button } from 'semantic-ui-react'

export const userColumns = ({ handleClick }) => [
  {
    Header: 'User',
    accessor: 'Username',
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

export const groupColumns = ({ handleClick }) => [
  {
    Header: 'Group Name',
    accessor: 'GroupName',
  },
  {
    Header: 'Description',
    accessor: 'Description',
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
