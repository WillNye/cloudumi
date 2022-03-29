import { Bar } from 'lib/Misc'
import React from 'react'

import { Button } from 'semantic-ui-react'

export const userColumns = ({ handleClick }) => [
  {
    Header: 'User',
    accessor: 'Username',
  },
  {
    Header: 'Actions',
    width: 120,
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
    width: 120,
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
