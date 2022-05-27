import React, { useState } from 'react'
import {
  Button,
  Grid,
  Header,
  Table,
  Segment,
  Loader,
  Dimmer,
} from 'semantic-ui-react'
import { useAuth } from '../../auth/AuthProviderDefault'
import { validateApprovePolicy } from '../../helpers/utils'
import {
  AppliedNotification,
  CancelledNotification,
  ExpiredNotification,
  ReadOnlyNotification,
  ResponseNotification,
} from './notificationMessages'

const TemporaryEscalationComponent = (props) => {
  const change = props.change
  const [isLoading, setIsLoading] = useState(false)
  const [buttonResponseMessage, setButtonResponseMessage] = useState([])
  const { sendProposedPolicyWithHooks } = useAuth()

  const handleApproval = async () => {
    await sendProposedPolicyWithHooks(
      'apply_change',
      change,
      null,
      props.requestID,
      setIsLoading,
      setButtonResponseMessage,
      props.reloadDataFromBackend
    )
  }

  const handleCancel = async () => {
    await sendProposedPolicyWithHooks(
      'cancel_change',
      change,
      null,
      props.requestID,
      setIsLoading,
      setButtonResponseMessage,
      props.reloadDataFromBackend
    )
  }

  const isOwner =
    validateApprovePolicy(props.changesConfig, change.id) ||
    props.config.can_approve_reject

  const isReadonlyInfo =
    (props.requestReadOnly && change.status === 'not_applied') ||
    (!props.config.can_update_cancel && !isOwner)

  const headerContent = (
    <Header size='large'>Temporary Escalation Access Request</Header>
  )

  const applyChangesButton =
    isOwner && change.status === 'not_applied' && !props.requestReadOnly ? (
      <Grid.Column>
        <Button
          content='Apply Change'
          onClick={handleApproval}
          positive
          fluid
        />
      </Grid.Column>
    ) : null

  const cancelChangesButton =
    isOwner && change.status === 'not_applied' && !props.requestReadOnly ? (
      <Grid.Column>
        <Button content='Cancel Change' onClick={handleCancel} negative fluid />
      </Grid.Column>
    ) : null

  const requestDetailsContent = change ? (
    <Table celled definition striped>
      <Table.Body>
        <Table.Row>
          <Table.Cell>User</Table.Cell>
          <Table.Cell>{props.requesterEmail}</Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>Role</Table.Cell>
          <Table.Cell>{change.principal.principal_arn}</Table.Cell>
        </Table.Row>
      </Table.Body>
    </Table>
  ) : null

  const policyChangeContent = change ? (
    <Grid fluid>
      <Grid.Row columns='equal'>
        <Grid.Column>{requestDetailsContent}</Grid.Column>
      </Grid.Row>
      <Grid.Row columns='equal'>
        <Grid.Column>
          <ResponseNotification response={buttonResponseMessage} />
        </Grid.Column>
      </Grid.Row>
      <Grid.Row columns='equal'>
        {applyChangesButton}
        {cancelChangesButton}
        <ReadOnlyNotification isReadonlyInfo={isReadonlyInfo} />
        <AppliedNotification isApplied={change.status === 'applied'} />
        <CancelledNotification isCancelled={change.status === 'cancelled'} />
        <ExpiredNotification isExpired={change.status === 'expired'} />
      </Grid.Row>
    </Grid>
  ) : null

  return (
    <Segment>
      <Dimmer active={isLoading} inverted>
        <Loader />
      </Dimmer>
      {headerContent}
      {policyChangeContent}
    </Segment>
  )
}

export default TemporaryEscalationComponent
