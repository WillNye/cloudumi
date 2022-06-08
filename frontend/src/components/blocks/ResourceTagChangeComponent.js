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

const ResourceTagChangeComponent = (props) => {
  const change = props.change
  const [isLoading, setIsLoading] = useState(false)
  const [buttonResponseMessage, setButtonResponseMessage] = useState([])
  const { sendProposedPolicyWithHooks } = useAuth()

  const getTagActionSpan = () => {
    if (change.tag_action === 'create') {
      return <span style={{ color: 'green' }}>Create</span>
    }
    if (change.tag_action === 'update') {
      return <span style={{ color: 'green' }}>Update</span>
    }
    if (change.tag_action === 'delete') {
      return <span style={{ color: 'red' }}>Delete</span>
    }
  }
  const action = getTagActionSpan(change)

  const handleTaggingApprove = async () => {
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

  const handleTaggingCancel = async () => {
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

  const allowedAdmins = getAllowedResourceAdmins(props.changesConfig, change.id)

  const headerContent = (
    <Header size='large'>
      Tag Change - {action} {change.key}
    </Header>
  )

  const applyChangesButton =
    isOwner && change.status === 'not_applied' && !props.requestReadOnly ? (
      <Grid.Column>
        <Button
          content='Apply Change'
          onClick={handleTaggingApprove}
          positive
          fluid
        />
      </Grid.Column>
    ) : null

  const cancelChangesButton =
    isOwner && change.status === 'not_applied' && !props.requestReadOnly ? (
      <Grid.Column>
        <Button
          content='Cancel Change'
          onClick={handleTaggingCancel}
          negative
          fluid
        />
      </Grid.Column>
    ) : null

  const isReadonlyInfo =
    (props.requestReadOnly && change.status === 'not_applied') || !isOwner

  const originalTagKey =
    change.original_key && change.original_key !== change.key ? (
      <Table.Row>
        <Table.Cell>
          Previous Tag Key Name (Approving will rename the tag)
        </Table.Cell>
        <Table.Cell>{change.original_key}</Table.Cell>
      </Table.Row>
    ) : null

  const desiredTagKey = change.key ? (
    <Table.Row>
      <Table.Cell>Key</Table.Cell>
      <Table.Cell positive>{change.key}</Table.Cell>
    </Table.Row>
  ) : null

  const originalTagValue =
    change.value &&
    change.original_value &&
    change.original_value !== change.value ? (
      <Table.Row>
        <Table.Cell>
          Previous Tag Value (Approving will change the value)
        </Table.Cell>
        <Table.Cell>{change.original_value}</Table.Cell>
      </Table.Row>
    ) : null

  const desiredTagValue = change.value ? (
    <Table.Row>
      <Table.Cell>Value</Table.Cell>
      <Table.Cell positive>{change.value}</Table.Cell>
    </Table.Row>
  ) : null

  const requestDetailsContent = change ? (
    <Table celled definition striped>
      <Table.Body>
        {originalTagKey}
        {desiredTagKey}
        {originalTagValue}
        {desiredTagValue}
        <Table.Row>
          <Table.Cell>Action</Table.Cell>
          {change.tag_action === 'create' ? (
            <Table.Cell positive>Create</Table.Cell>
          ) : null}
          {change.tag_action === 'update' ? (
            <Table.Cell positive>Update</Table.Cell>
          ) : null}
          {change.tag_action === 'delete' ? (
            <Table.Cell negative>Delete</Table.Cell>
          ) : null}
        </Table.Row>
        <Table.Row>
          <Table.Cell>ARN</Table.Cell>
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
            onLintError={null}
            onValueChange={null}
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

export default ResourceTagChangeComponent
