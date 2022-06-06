import React, { Component } from 'react'
import {
  Button,
  Dimmer,
  Divider,
  Grid,
  Header,
  Loader,
  Message,
  Segment,
  Table,
  Icon,
  Accordion,
} from 'semantic-ui-react'
import MonacoDiffComponent from './MonacoDiffComponent'
import {
  getAllowedResourceAdmins,
  sortAndStringifyNestedJSONObject,
  validateApprovePolicy,
} from '../../helpers/utils'
import {
  AppliedNotification,
  CancelledNotification,
  ExpiredNotification,
  ReadOnlyNotification,
  ResponseNotification,
} from './notificationMessages'

class InlinePolicyChangeComponent extends Component {
  constructor(props) {
    super(props)
    const { change, config, requestReadOnly, requestID, changesConfig } = props
    const oldPolicyDoc =
      change.old_policy && change.old_policy.policy_document
        ? change.old_policy.policy_document
        : {}

    const newPolicyDoc =
      change.policy.policy_document && change.policy.policy_document
        ? change.policy.policy_document
        : {}
    const newStatement = sortAndStringifyNestedJSONObject(newPolicyDoc)

    this.state = {
      newStatement,
      lastSavedStatement: newStatement,
      isError: false,
      messages: [],
      buttonResponseMessage: [],
      oldStatement: sortAndStringifyNestedJSONObject(oldPolicyDoc),
      change,
      config,
      changesConfig: changesConfig || {},
      requestReadOnly,
      requestID,
      isLoading: false,
      showAllowedAdmins: false,
    }

    this.onLintError = this.onLintError.bind(this)
    this.onValueChange = this.onValueChange.bind(this)
    this.onSubmitChange = this.onSubmitChange.bind(this)
    this.handleShowAdmins = this.handleShowAdmins.bind(this)
    this.updatePolicyDocument = props.updatePolicyDocument
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
          const oldPolicyDoc =
            change.old_policy && change.old_policy.policy_document
              ? change.old_policy.policy_document
              : {}

          const newPolicyDoc =
            change.policy.policy_document && change.policy.policy_document
              ? change.policy.policy_document
              : {}
          const newStatement = sortAndStringifyNestedJSONObject(newPolicyDoc)
          this.setState({
            newStatement,
            lastSavedStatement: newStatement,
            oldStatement: sortAndStringifyNestedJSONObject(oldPolicyDoc),
            change,
            config,
            requestReadOnly,
            isLoading: false,
          })
        }
      )
    }
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

  onSubmitChange() {
    const applyChange = this.props.sendProposedPolicy.bind(this, 'apply_change')
    applyChange()
  }

  handleShowAdmins() {
    const { showAllowedAdmins } = this.state
    this.setState({ showAllowedAdmins: !showAllowedAdmins })
  }

  render() {
    const {
      oldStatement,
      newStatement,
      change,
      changesConfig,
      config,
      isError,
      messages,
      requestReadOnly,
      lastSavedStatement,
      isLoading,
      buttonResponseMessage,
      showAllowedAdmins,
    } = this.state

    const isOwner =
      validateApprovePolicy(changesConfig, change.id) ||
      config.can_approve_reject

    const allowedAdmins = getAllowedResourceAdmins(changesConfig, change.id)

    const newPolicy = change.new ? (
      <span style={{ color: 'red' }}>- New Policy</span>
    ) : null

    const headerContent = () => {
      if (change.change_type === 'inline_policy') {
        return (
          <Header size='large'>
            Inline Policy Change - {change.policy_name} {newPolicy}
          </Header>
        )
      } else {
        return <Header size='large'>Managed Policy Change</Header>
      }
    }

    const applyChangesButton =
      isOwner && change.status === 'not_applied' && !requestReadOnly ? (
        <Grid.Column>
          <Button
            content='Apply Change'
            positive
            fluid
            disabled={isError}
            onClick={this.onSubmitChange}
          />
        </Grid.Column>
      ) : null

    const noChangesDetected = lastSavedStatement === newStatement

    const updateChangesButton =
      (validateApprovePolicy(changesConfig, change.id) ||
        config.can_update_cancel) &&
      change.status === 'not_applied' &&
      !requestReadOnly ? (
        <Grid.Column>
          <Button
            content='Update Change'
            positive
            fluid
            disabled={isError || noChangesDetected}
            onClick={this.props.sendProposedPolicy.bind(this, 'update_change')}
          />
        </Grid.Column>
      ) : null

    const cancelChangesButton =
      (config.can_update_cancel || isOwner) &&
      change.status === 'not_applied' &&
      !requestReadOnly ? (
        <Grid.Column>
          <Button
            content='Cancel Change'
            negative
            fluid
            disabled={isError}
            onClick={this.props.sendProposedPolicy.bind(this, 'cancel_change')}
          />
        </Grid.Column>
      ) : null

    const isReadonlyInfo =
      (requestReadOnly && change.status === 'not_applied') ||
      (!config.can_update_cancel && !isOwner)

    const messagesToShow =
      messages.length > 0 ? (
        <Message negative>
          <Message.Header>There was a problem with your request</Message.Header>
          <Message.List>
            {messages.map((message) => (
              <Message.Item>{message}</Message.Item>
            ))}
          </Message.List>
        </Message>
      ) : null

    const changeReadOnly =
      requestReadOnly ||
      change.status === 'applied' ||
      change.status === 'cancelled'

    const policyChangeContent = change ? (
      <Grid fluid>
        <Grid.Row>
          <Grid.Column>
            <Accordion>
              <Accordion.Title
                active={showAllowedAdmins}
                onClick={this.handleShowAdmins}
              >
                <Icon name='dropdown' />
                Show Aprrovers
              </Accordion.Title>
              <Accordion.Content active={showAllowedAdmins}>
                <Table celled>
                  <Table.Header>
                    <Table.Row>
                      <Table.HeaderCell>User/Group</Table.HeaderCell>
                      <Table.HeaderCell>Can Approve</Table.HeaderCell>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {allowedAdmins.map((userGroup) => (
                      <Table.Row>
                        <Table.Cell>{userGroup}</Table.Cell>
                        <Table.Cell positive>
                          <Icon name='checkmark' />
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              </Accordion.Content>
            </Accordion>
          </Grid.Column>
        </Grid.Row>

        <Grid.Row columns='equal'>
          <Grid.Column>
            <Header
              size='medium'
              content='Current Policy'
              subheader='This is a read-only view of the current policy in AWS.'
            />
          </Grid.Column>
          <Grid.Column>
            <Header
              size='medium'
              content='Proposed Policy'
              subheader='This is an editable view of the proposed policy.
              An approver can modify the proposed policy before approving and applying it.'
            />
          </Grid.Column>
        </Grid.Row>

        <Grid.Row>
          <Grid.Column>
            <MonacoDiffComponent
              oldValue={oldStatement}
              newValue={newStatement}
              readOnly={
                (!config.can_update_cancel && !isOwner) || changeReadOnly
              }
              onLintError={this.onLintError}
              onValueChange={this.onValueChange}
              showIac={true}
              policyName={change.policy_name}
              principal={change.principal}
            />
          </Grid.Column>
        </Grid.Row>
        <Grid.Row columns='equal'>
          <Grid.Column>{messagesToShow}</Grid.Column>
        </Grid.Row>
        <Grid.Row columns='equal'>
          <Grid.Column>
            <ResponseNotification response={buttonResponseMessage} />
          </Grid.Column>
        </Grid.Row>
        <Grid.Row columns='equal'>
          {applyChangesButton}
          {updateChangesButton}
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
        {headerContent()}
        <Divider hidden />
        {policyChangeContent}
      </Segment>
    )
  }
}

export default InlinePolicyChangeComponent
