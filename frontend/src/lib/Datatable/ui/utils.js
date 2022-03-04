import React from 'react'
import { Button, Segment } from 'semantic-ui-react'
import styled from 'styled-components'
import { Bar } from '../../Misc'

const CustomTopBar = styled(Bar)`
  margin: 0 0 25px;
`

const CustomBar = styled(Bar)`
  display: block;
`

export const DatatableWrapper = ({ renderAction, children, isLoading }) => {
  const renderTopBar = renderAction && (
    <CustomTopBar>{renderAction}</CustomTopBar>
  )

  return (
    <Segment loading={isLoading}>
      {renderTopBar}
      <CustomBar basic>{children}</CustomBar>
    </Segment>
  )
}

export const EmptyState = ({ label, onClick }) => {
  return (
    <Segment basic inverted color='grey' textAlign='center'>
      <Button onClick={onClick}>{label}</Button>
    </Segment>
  )
}

export const LoadingState = ({ label }) => {
  return (
    <Segment basic inverted color='grey' textAlign='center'>
      <Button disabled>{label}</Button>
    </Segment>
  )
}

export const RefreshButton = ({ disabled, onClick = () => {} }) => {
  return (
    <Button compact disabled={disabled} icon='refresh' onClick={() => onClick()} />
  )
}
