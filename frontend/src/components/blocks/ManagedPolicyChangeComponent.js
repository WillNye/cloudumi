import React, { Component } from 'react'
import {
  Button,
  Grid,
  Header,
  Table,
  Segment,
  Loader,
  Dimmer,
} from 'semantic-ui-react'
import {
  getAllowedResourceAdmins,
  validateApprovePolicy,
} from '../../helpers/utils'
import {
  AppliedNotification,
  CancelledNotification,
  ExpiredNotification,
  ReadOnlyNotification,
  ResponseNotification,
} from './notificationMessages'
import MonacoDiffComponent from './MonacoDiffComponent'
import ResourceChangeApprovers from './ResourceChangeApprovers'
import ReadOnlyApprovalModal from './modals/ReadOnlyApprovalModal'

class ManagedPolicyChangeComponent extends Component {
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
      isApprovalModalOpen: false,
    }

    this.onSubmitChange = this.onSubmitChange.bind(this)
    this.onCancelChange = this.onCancelChange.bind(this)
    this.setIsApprovalModalOpen = this.setIsApprovalModalOpen.bind(this)
    this.handleOnSubmitChange = this.handleOnSubmitChange.bind(this)
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

  setIsApprovalModalOpen(value) {
    this.setState({ isApprovalModalOpen: value })
  }

  handleOnSubmitChange() {
    const { change } = this.props
    if (change.read_only) {
      this.setIsApprovalModalOpen(true)
    } else {
      this.onSubmitChange()
    }
  }

  onSubmitChange(credentials = null) {
    const applyChange = this.props.sendProposedPolicy.bind(
      this,
      'apply_change',
      credentials
    )
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
      isApprovalModalOpen,
    } = this.state

    const isOwner =
      validateApprovePolicy(changesConfig, change.id) ||
      config.can_approve_reject

    const allowedAdmins = getAllowedResourceAdmins(changesConfig, change.id)

    const action =
      change.action === 'detach' ? (
        <span style={{ color: 'red' }}>Detach</span>
      ) : (
        <span style={{ color: 'green' }}>Attach</span>
      )

    const headerContent = (
      <Header size='large'>
        Managed Policy Change - {action} {change.policy_name}
      </Header>
    )

    const applyChangesButton =
      isOwner && change.status === 'not_applied' && !requestReadOnly ? (
        <Grid.Column>
          <Button
            content='Apply Change'
            positive
            fluid
            onClick={this.handleOnSubmitChange}
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

    const policyChangeContent = change ? (
      <Grid fluid>
        <ResourceChangeApprovers allowedAdmins={allowedAdmins} />
        <Grid.Row columns='equal'>
          <Grid.Column>{requestDetailsContent}</Grid.Column>
        </Grid.Row>
        <Grid.Row columns='equal'>
          <Grid.Column>
            <ResponseNotification response={buttonResponseMessage} />
          </Grid.Column>
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
              enableJSON={true}
              enableTerraform={false}
              enableCloudFormation={false}
            />
          </Grid.Column>
        </Grid.Row>
        <Grid.Row columns='equal'>
          {applyChangesButton}
          {cancelChangesButton}
          <ReadOnlyNotification
            isReadonlyInfo={requestReadOnly && change.status === 'not_applied'}
          />
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
        <ReadOnlyApprovalModal
          onSubmitChange={this.onSubmitChange}
          isApprovalModalOpen={isApprovalModalOpen}
          setIsApprovalModalOpen={this.setIsApprovalModalOpen}
        />
      </Segment>
    )
  }
}

export default ManagedPolicyChangeComponent
