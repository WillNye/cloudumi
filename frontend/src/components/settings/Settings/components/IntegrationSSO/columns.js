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
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <Button size='mini' onClick={() => handleClick('remove', row?.values)}>
        Remove
      </Button>
    ),
  },
]
