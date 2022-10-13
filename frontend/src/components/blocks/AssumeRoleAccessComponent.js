import { useState } from 'react'
import {
  Button,
  Grid,
  Header,
  Table,
  Segment,
  Loader,
  Dimmer,
  Label,
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
import ReadOnlyApprovalModal from './modals/ReadOnlyApprovalModal'

const AssumeRole = (props) => {
  const change = props.change
  const [isLoading, setIsLoading] = useState(false)
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false)
  const [buttonResponseMessage, setButtonResponseMessage] = useState([])
  const { sendProposedPolicyWithHooks } = useAuth()

  const getTagActionSpan = () => {
    if (change.action === 'add') {
      return <span style={{ color: 'green' }}>Add</span>
    }
    if (change.action === 'remove') {
      return <span style={{ color: 'red' }}>Delete</span>
    }
  }
  const action = getTagActionSpan(change)

  const handleTaggingApprove = async (credentials = null) => {
    await sendProposedPolicyWithHooks(
      'apply_change',
      change,
      null,
      props.requestID,
      setIsLoading,
      setButtonResponseMessage,
      props.reloadDataFromBackend,
      credentials
    )
  }

  const handleOnSubmitChange = () => {
    if (change.read_only) {
      setIsApprovalModalOpen(true)
    } else {
      handleTaggingApprove()
    }
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
      Role Request Change - {action} {change.key}
    </Header>
  )

  const applyChangesButton =
    isOwner && change.status === 'not_applied' && !props.requestReadOnly ? (
      <Grid.Column>
        <Button
          content='Apply Change'
          onClick={handleOnSubmitChange}
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

  const desiredTagValue = change.identities ? (
    <Table.Row>
      <Table.Cell>Users/Groups</Table.Cell>
      <Table.Cell>
        {change.identities.map((group) => (
          <Label>{group}</Label>
        ))}
      </Table.Cell>
    </Table.Row>
  ) : null

  const requestDetailsContent = change ? (
    <Table celled definition striped>
      <Table.Body>
        <Table.Row>
          <Table.Cell>Action</Table.Cell>
          {change.action === 'add' ? (
            <Table.Cell positive>Add</Table.Cell>
          ) : null}
          {change.action === 'remove' ? (
            <Table.Cell negative>Delete</Table.Cell>
          ) : null}
        </Table.Row>
        <Table.Row>
          <Table.Cell>ARN</Table.Cell>
          <Table.Cell>{change.principal.principal_arn}</Table.Cell>
        </Table.Row>
        {desiredTagValue}
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
      <ReadOnlyApprovalModal
        onSubmitChange={handleTaggingApprove}
        isApprovalModalOpen={isApprovalModalOpen}
        setIsApprovalModalOpen={setIsApprovalModalOpen}
      />
    </Segment>
  )
}

export default AssumeRole
