import { Bar } from 'lib/Misc'
import React from 'react'

import { Button } from 'semantic-ui-react'

export const integrationSSOColumns = ({ handleClick }) => [
  {
    Header: 'Provider Name',
    accessor: 'provider_name',
  },
  {
    Header: 'Provider Type',
    accessor: 'provider_type',
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
