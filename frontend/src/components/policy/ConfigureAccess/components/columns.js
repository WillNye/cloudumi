import React from 'react'
import { Button, Checkbox } from 'semantic-ui-react'

export const tempEscalationColumns = ({ handleRemove, disabled }) => [
  {
    Header: 'Group',
    accessor: 'group_name',
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button
        size='mini'
        onClick={() => handleRemove(row?.original)}
        disabled={disabled}
      >
        Remove
      </Button>
    ),
  },
]

export const roleAccessColumns = ({ handleRemove, disabled }) => [
  {
    Header: 'Group',
    accessor: 'group_name',
  },
  {
    Header: 'Allow Web Access',
    accessor: 'web_access',
    align: 'center',
    Cell: ({ row }) => (
      <Checkbox toggle defaultChecked={row?.original?.web_access} disabled />
    ),
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button
        size='mini'
        onClick={() => handleRemove(row?.original)}
        disabled={disabled}
      >
        Remove
      </Button>
    ),
  },
]
