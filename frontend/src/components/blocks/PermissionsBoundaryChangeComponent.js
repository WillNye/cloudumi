import React, { Component } from 'react'
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
import { validateApprovePolicy } from '../../helpers/utils'
import MonacoDiffComponent from './MonacoDiffComponent'

class PermissionsBoundaryChangeComponent extends Component {
  constructor(props) {
    super(props)
    this.state = {
      isLoading: false,
      messages: [],
      buttonResponseMessage: [],
      change: this.props.change,
      config: this.props.config,
      changesConfig: this.props.changesConfig || {},
      requestID: this.props.requestID,
      requestReadOnly: this.props.requestReadOnly,
    }

    this.onSubmitChange = this.onSubmitChange.bind(this)
    this.onCancelChange = this.onCancelChange.bind(this)
    this.reloadDataFromBackend = props.reloadDataFromBackend
  }

  componentDidUpdate(prevProps) {
    if (
      JSON.stringify(prevProps.change) !== JSON.stringify(this.props.change) ||
      prevProps.requestReadOnly !== this.props.requestReadOnly
    ) {
      this.setState(
        {
          isLoading: true,
        },
        () => {
          const { change, config, requestReadOnly } = this.props
          this.setState({
            change,
            config,
            requestReadOnly,
            isLoading: false,
          })
        }
      )
    }
  }

  onSubmitChange() {
    const applyChange = this.props.sendProposedPolicy.bind(this, 'apply_change')
    applyChange()
  }

  onCancelChange() {
    const cancelChange = this.props.sendProposedPolicy.bind(
      this,
      'cancel_change'
    )
    cancelChange()
  }

  onLintError(lintErrors) {
    if (lintErrors.length > 0) {
      this.setState({
        messages: lintErrors,
        isError: true,
      })
    } else {
      this.setState({
        messages: [],
        isError: false,
      })
    }
  }

  onValueChange(newValue) {
    const { change } = this.state
    this.setState({
      newStatement: newValue,
      buttonResponseMessage: [],
    })
    this.updatePolicyDocument(change.id, newValue)
  }

  render() {
    const {
      change,
      config,
      requestReadOnly,
      isLoading,
      buttonResponseMessage,
      changesConfig,
    } = this.state

    const isOwner =
      validateApprovePolicy(changesConfig, change.id) ||
      config.can_approve_reject

    const action =
      change.action === 'detach' ? (
        <span style={{ color: 'red' }}>Detach</span>
      ) : (
        <span style={{ color: 'green' }}>Attach</span>
      )

    const headerContent = (
      <Header size='large'>
        Permissions Boundary Change - {action} {change.policy_name}
      </Header>
    )

    const applyChangesButton =
      isOwner && change.status === 'not_applied' && !requestReadOnly ? (
        <Grid.Column>
          <Button
            content='Apply Change'
            positive
            fluid
            onClick={this.onSubmitChange}
          />
        </Grid.Column>
      ) : null

    const cancelChangesButton =
      (isOwner || config.can_update_cancel) &&
      change.status === 'not_applied' &&
      !requestReadOnly ? (
        <Grid.Column>
          <Button
            content='Cancel Change'
            negative
            fluid
            onClick={this.onCancelChange}
          />
        </Grid.Column>
      ) : null

    const isReadonlyInfo =
      (requestReadOnly && change.status === 'not_applied') ||
      (!config.can_update_cancel && !isOwner)
    const viewOnlyInfo = isReadonlyInfo ? (
      <Grid.Column>
        <Message info>
          <Message.Header>View only</Message.Header>
          <p>This change is view only and can no longer be modified.</p>
        </Message>
      </Grid.Column>
    ) : null

    const changesAlreadyAppliedContent =
      change.status === 'applied' ? (
        <Grid.Column>
          <Message positive>
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
            <Table.Cell>Policy ARN</Table.Cell>
            <Table.Cell>{change.arn}</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Action</Table.Cell>
            {change.action === 'detach' ? (
              <Table.Cell negative>Detach</Table.Cell>
            ) : (
              <Table.Cell positive>Attach</Table.Cell>
            )}
          </Table.Row>
          <Table.Row>
            <Table.Cell>Role ARN</Table.Cell>
            <Table.Cell>{change.principal.principal_arn}</Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
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

    const policyChangeContent = change ? (
      <Grid fluid>
        <Grid.Row columns='equal'>
          <Grid.Column>{requestDetailsContent}</Grid.Column>
        </Grid.Row>
        <Grid.Row columns='equal'>
          <Grid.Column>{responseMessagesToShow}</Grid.Column>
        </Grid.Row>
        <Grid.Row>
          <Grid.Column>
            <MonacoDiffComponent
              oldValue={''}
              newValue={''}
              readOnly={true}
              onLintError={this.onLintError}
              onValueChange={this.onValueChange}
              showIac={true}
              pythonScript={change?.python_script}
              enableJSON={false}
              enableTerraform={false}
              enableCloudFormation={false}
            />
          </Grid.Column>
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
}

export default PermissionsBoundaryChangeComponent
