import React from 'react'
import { Button } from 'semantic-ui-react'

export const tempEscalationColumns = ({ handleRemove }) => [
  {
    Header: 'Group',
    accessor: 'group_name',
  },
  {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button size='mini' onClick={() => handleRemove(row?.original)}>
        Remove
      </Button>
    ),
  },
]
