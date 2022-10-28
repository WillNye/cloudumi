import { useState } from 'react'
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
import ResourceChangeApprovers from './ResourceChangeApprovers'
import ReadOnlyApprovalModal from './modals/ReadOnlyApprovalModal'
import { useMemo } from 'react'

const ResourceTypePolicyComponent = (props) => {
  const change = props.change
  const [isLoading, setIsLoading] = useState(false)
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false)
  const [buttonResponseMessage, setButtonResponseMessage] = useState([])
  const { sendProposedPolicyWithHooks } = useAuth()

  const isCreateRequest = useMemo(() => {
    return change.change_type === 'create_resource'
  }, [change.change_type])

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
      {isCreateRequest ? 'Create Resource' : 'Delete Resource'}
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

  const requestDetailsContent = change ? (
    <Table celled definition striped>
      <Table.Body>
        <Table.Row>
          <Table.Cell>Resource Type</Table.Cell>
          <Table.Cell>{change.principal.resource_type}</Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>Account Id</Table.Cell>
          <Table.Cell>{change.principal.account_id}</Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell>Resource Name</Table.Cell>
          <Table.Cell>{change.principal.name}</Table.Cell>
        </Table.Row>
        {change?.description && (
          <Table.Row>
            <Table.Cell>Description</Table.Cell>
            <Table.Cell>{change.description}</Table.Cell>
          </Table.Row>
        )}
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

export default ResourceTypePolicyComponent
