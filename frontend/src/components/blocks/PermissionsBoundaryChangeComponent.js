import React, { useCallback, useState } from 'react'
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
import { useAuth } from 'auth/AuthProviderDefault'

const PermissionsBoundaryChangeComponent = (props) => {
  const {
    change,
    changesConfig,
    config,
    requestReadOnly,
    reloadDataFromBackend,
    requestID,
  } = props

  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [buttonResponseMessage, setButtonResponseMessage] = useState([])

  const { sendProposedPolicyWithHooks } = useAuth()

  const handleOnSubmitChange = () => {
    if (change.read_only) {
      setIsApprovalModalOpen(true)
    } else {
      onSubmitChange()
    }
  }

  const handleCancel = useCallback(async () => {
    await sendProposedPolicyWithHooks(
      'cancel_change',
      change,
      null,
      requestID,
      setIsLoading,
      setButtonResponseMessage,
      reloadDataFromBackend
    )
  }, [change, requestID]) // eslint-disable-line react-hooks/exhaustive-deps

  const onSubmitChange = useCallback(
    async (credentials = null) => {
      await sendProposedPolicyWithHooks(
        'apply_change',
        change,
        null,
        requestID,
        setIsLoading,
        setButtonResponseMessage,
        reloadDataFromBackend,
        credentials
      )
    },
    [change, requestID] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const isOwner =
    validateApprovePolicy(changesConfig, change.id) || config.can_approve_reject

  const allowedAdmins = getAllowedResourceAdmins(changesConfig, change.id)

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
          onClick={handleOnSubmitChange}
        />
      </Grid.Column>
    ) : null

  const cancelChangesButton =
    (isOwner || config.can_update_cancel) &&
    change.status === 'not_applied' &&
    !requestReadOnly ? (
      <Grid.Column>
        <Button content='Cancel Change' negative fluid onClick={handleCancel} />
      </Grid.Column>
    ) : null

  const isReadonlyInfo =
    (requestReadOnly && change.status === 'not_applied') ||
    (!config.can_update_cancel && !isOwner)

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
      <ReadOnlyApprovalModal
        onSubmitChange={onSubmitChange}
        isApprovalModalOpen={isApprovalModalOpen}
        setIsApprovalModalOpen={setIsApprovalModalOpen}
      />
    </Segment>
  )
}

export default PermissionsBoundaryChangeComponent
