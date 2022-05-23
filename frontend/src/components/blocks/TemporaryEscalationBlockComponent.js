import React, { useState } from 'react'
import {
  Button,
  Grid,
  Header,
  Message,
  Table,
  Segment,
  Loader,
  Dimmer,
} from 'semantic-ui-react'
import { useAuth } from '../../auth/AuthProviderDefault'
import { validateApprovePolicy } from '../../helpers/utils'

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

  const viewOnlyInfo =
    props.requestReadOnly && change.status === 'not_applied' ? (
      <Grid.Column>
        <Message info>
          <Message.Header>View only</Message.Header>
          <p>This change is view only and can no longer be modified.</p>
        </Message>
      </Grid.Column>
    ) : null

  const responseMessagesToShow =
    buttonResponseMessage.length > 0 ? (
      <Grid.Column>
        {buttonResponseMessage.map((message) =>
          message.status === 'error' ? (
            <Message negative>
              <Message.Header>An error occurred</Message.Header>
              <Message.Content>{message.message}</Message.Content>
            </Message>
          ) : (
            <Message positive>
              <Message.Header>Success</Message.Header>
              <Message.Content>{message.message}</Message.Content>
            </Message>
          )
        )}
      </Grid.Column>
    ) : null

  const changesAlreadyAppliedContent =
    change.status === 'applied' ? (
      <Grid.Column>
        <Message info>
          <Message.Header>Change already applied</Message.Header>
          <p>This change has already been applied and cannot be modified.</p>
        </Message>
      </Grid.Column>
    ) : null

  const changesAlreadyCancelledContent =
    change.status === 'cancelled' ? (
      <Grid.Column>
        <Message negative>
          <Message.Header>Change cancelled</Message.Header>
          <p>This change has been cancelled and cannot be modified.</p>
        </Message>
      </Grid.Column>
    ) : null

  const changesExpiredContent =
    change.status === 'expired' ? (
      <Grid.Column>
        <Message negative>
          <Message.Header>Change expired</Message.Header>
          <p>This change has expired and cannot be modified.</p>
        </Message>
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
        <Grid.Column>{responseMessagesToShow}</Grid.Column>
      </Grid.Row>
      <Grid.Row columns='equal'>
        {applyChangesButton}
        {cancelChangesButton}
        {viewOnlyInfo}
        {changesAlreadyAppliedContent}
        {changesAlreadyCancelledContent}
        {changesExpiredContent}
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
