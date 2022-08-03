import React, { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Dimmer,
  Divider,
  Grid,
  Header,
  Loader,
  Message,
  Segment,
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
import ResourceChangeApprovers from './ResourceChangeApprovers'
import ReadOnlyApprovalModal from './modals/ReadOnlyApprovalModal'
import { useAuth } from 'auth/AuthProviderDefault'

const InlinePolicyChangeComponent = (props) => {
  const {
    change,
    config,
    requestReadOnly,
    requestID,
    changesConfig = {},
    reloadDataFromBackend,
    updatePolicyDocument,
  } = props

  const [isError, setIsError] = useState()
  const [newStatement, setNewStatement] = useState('')
  const [oldStatement, setOldStatement] = useState('')
  const [lastSavedStatement, setLastSavedStatement] = useState('')
  const [messages, setMessages] = useState([])
  const [buttonResponseMessage, setButtonResponseMessage] = useState([])
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const { sendProposedPolicyWithHooks } = useAuth()

  const noChangesDetected = lastSavedStatement === newStatement

  useEffect(() => {
    const oldPolicyDoc = change?.old_policy?.policy_document
      ? change.old_policy.policy_document
      : {}

    const newPolicyDoc = change?.policy?.policy_document
      ? change.policy.policy_document
      : {}

    const stringifiedNewPolicy = sortAndStringifyNestedJSONObject(newPolicyDoc)
    const stringifiedOldPolicy = sortAndStringifyNestedJSONObject(oldPolicyDoc)

    setNewStatement(stringifiedNewPolicy)
    setLastSavedStatement(stringifiedNewPolicy)
    setOldStatement(stringifiedOldPolicy)
  }, [change])

  const onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setMessages(lintErrors)
      setIsError(true)
    } else {
      setMessages([])
      setIsError(false)
    }
  }

  const onValueChange = useCallback(
    (newValue) => {
      setNewStatement(newValue)
      setButtonResponseMessage([])
      updatePolicyDocument(change.id, newValue)
    },
    [change.id] // eslint-disable-line react-hooks/exhaustive-deps
  )

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

  const handleUpdate = useCallback(async () => {
    await sendProposedPolicyWithHooks(
      'update_change',
      change,
      newStatement,
      requestID,
      setIsLoading,
      setButtonResponseMessage,
      reloadDataFromBackend
    )
  }, [change, requestID, newStatement]) // eslint-disable-line react-hooks/exhaustive-deps

  const onSubmitChange = useCallback(
    async (credentials = null) => {
      await sendProposedPolicyWithHooks(
        'apply_change',
        change,
        newStatement,
        requestID,
        setIsLoading,
        setButtonResponseMessage,
        reloadDataFromBackend,
        credentials
      )
    },
    [change, requestID, newStatement] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const handleOnSubmitChange = useCallback(() => {
    if (change.read_only) {
      setIsApprovalModalOpen(true)
    } else {
      onSubmitChange()
    }
  }, [change, onSubmitChange])

  const isOwner =
    validateApprovePolicy(changesConfig, change.id) || config.can_approve_reject

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
          onClick={handleOnSubmitChange}
        />
      </Grid.Column>
    ) : null

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
          onClick={handleUpdate}
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
          onClick={handleCancel}
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
          {messages.map((message, index) => (
            <Message.Item key={index}>{message}</Message.Item>
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
      <ResourceChangeApprovers allowedAdmins={allowedAdmins} />

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
            readOnly={(!config.can_update_cancel && !isOwner) || changeReadOnly}
            onLintError={onLintError}
            onValueChange={onValueChange}
            showIac={true}
            policyName={change.policy_name}
            principal={change.principal}
            enableJSON={true}
            enableTerraform={true}
            enableCloudFormation={true}
            pythonScript={change?.python_script}
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
      <ReadOnlyApprovalModal
        onSubmitChange={onSubmitChange}
        isApprovalModalOpen={isApprovalModalOpen}
        setIsApprovalModalOpen={setIsApprovalModalOpen}
      />
    </Segment>
  )
}

export default InlinePolicyChangeComponent
