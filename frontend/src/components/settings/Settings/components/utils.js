import React from 'react'
import { Button, Input } from 'semantic-ui-react'
import { Fill, Bar } from 'lib/Misc'

export const SectionTitle = ({ title, helpHandler }) => {
  const handleHelpModal = (handler) => {}

  return (
    <>
      <span>{title}</span>&nbsp;
      {helpHandler && (
        <Button
          size='mini'
          circular
          icon='question'
          basic
          onClick={() => handleHelpModal(helpHandler)}
        />
      )}
    </>
  )
}

export const TableTopBar = ({ onSearch, onClick, disabled }) => {
  return (
    <Bar>
      {onSearch && (
        <Input
          size='small'
          label='Search'
          icon='search'
          disabled={disabled}
          onChange={onSearch}
        />
      )}
      <Fill />
      <Button
        compact
        color='blue'
        onClick={onClick}
        disabled={disabled}
        style={{ marginRight: 0 }}
      >
        New
      </Button>
    </Bar>
  )
}
