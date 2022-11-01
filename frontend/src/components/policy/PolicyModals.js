import React, { useCallback, useState } from 'react'
import {
  Button,
  Checkbox,
  Dimmer,
  Divider,
  Form,
  Header,
  Loader,
  Message,
  Modal,
  TextArea,
} from 'semantic-ui-react'
import ReactMarkdown from 'react-markdown'
import { usePolicyContext } from './hooks/PolicyProvider'
import { Link } from 'react-router-dom'
import DateTimePicker from 'components/blocks/DateTimePicker'

const StatusMessage = ({ message, isSuccess }) => {
  if (message && isSuccess) {
    return (
      <Message positive>
        <Message.Header>Success</Message.Header>
        <Message.Content>
          <ReactMarkdown linkTarget='_blank' children={message} />
        </Message.Content>
      </Message>
    )
  }
  if (message && !isSuccess) {
    return (
      <Message negative>
        <Message.Header>Oops! There was a problem.</Message.Header>
        <Message.Content>
          <ReactMarkdown linkTarget='_blank' children={message} />
        </Message.Content>
      </Message>
    )
  }
  return null
}

export const JustificationModal = ({
  handleSubmit,
  showExpirationDate,
  showDetachManagedPolicy = false,
}) => {
  const {
    adminAutoApprove = false,
    context = 'inline_policy',
    isSuccess = false,
    resource = {},
    togglePolicyModal = false,
    setTogglePolicyModal,
    isPolicyEditorLoading,
    setIsPolicyEditorLoading,
    setIsSuccess,
  } = usePolicyContext()

  const [message, setMessage] = useState('')
  const [justification, setJustification] = useState('')
  const [expirationDate, setExpirationDate] = useState(null)
  const [detachManagedPolicy, setDetachManagedPolicy] = useState(true)

  const handleJustificationUpdate = (e) => {
    setJustification(e.target.value)
  }

  // TODO, there are too many state updates happening here. try do more in the reducer.
  const handleJustificationSubmit = useCallback(async () => {
    if (!justification) {
      setMessage('No empty justification is allowed.')
      setIsSuccess(false)
      return
    }
    setIsPolicyEditorLoading(true)

    const response = await handleSubmit({
      arn: resource.arn,
      adminAutoApprove,
      context,
      justification,
      expirationDate,
      detachManagedPolicies: detachManagedPolicy,
    })

    setMessage(response.message)
    setIsPolicyEditorLoading(false)
    setIsSuccess(response.request_created)
    setJustification('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    handleSubmit,
    justification,
    adminAutoApprove,
    detachManagedPolicy,
    expirationDate,
    context,
    resource,
  ])

  const handleSetPolicyExpiration = (value) => {
    const dateString = value ? new Date(value).toISOString() : value
    setExpirationDate(dateString)
  }

  const handleOk = () => {
    setMessage('')
    setJustification('')
    setIsSuccess(false)
    setTogglePolicyModal(false)
  }

  const handleCancel = () => {
    setMessage('')
    setJustification('')
    setIsSuccess(false)
    setTogglePolicyModal(false)
  }

  return (
    <Modal
      onClose={() => setTogglePolicyModal(false)}
      onOpen={() => setTogglePolicyModal(true)}
      open={togglePolicyModal}
      closeOnDimmerClick={false}
    >
      <Modal.Header>Please enter in your justification</Modal.Header>
      <Modal.Content>
        <Dimmer.Dimmable dimmed={isPolicyEditorLoading}>
          <StatusMessage isSuccess={isSuccess} message={message} />
          {!isSuccess && (
            <>
              {showDetachManagedPolicy && (
                <>
                  You are about to request a generated policy that contains all
                  of the actions taken by your AWS Identity in the past 90 days.
                  It will replace all of your existing inline policies, and if
                  desired, your managed policies as well. You will have the
                  opportunity to modify this policy before it is approved.
                  <br />
                  <br />
                </>
              )}
              <Form>
                <TextArea
                  placeholder='Tell us why you need this change'
                  onChange={handleJustificationUpdate}
                  style={{ width: 'fluid' }}
                  defaultValue={justification}
                />
              </Form>

              {showExpirationDate && (
                <>
                  <Header as='h6'>
                    <Header.Subheader>
                      (Optional) Set expiration date for requested policy. If no
                      date is set, the policy will not expire.
                    </Header.Subheader>
                  </Header>

                  <DateTimePicker
                    onDateSelectorChange={handleSetPolicyExpiration}
                  />
                </>
              )}

              {showDetachManagedPolicy && (
                <>
                  <Divider horizontal />
                  <Checkbox
                    label='Also Detach Existing Managed Policies'
                    onChange={(e, data) => setDetachManagedPolicy(data.checked)}
                    checked={detachManagedPolicy}
                  />
                </>
              )}
            </>
          )}

          <Dimmer active={isPolicyEditorLoading} inverted>
            <Loader />
          </Dimmer>
        </Dimmer.Dimmable>
      </Modal.Content>
      <Modal.Actions>
        {isSuccess ? (
          <Button
            content='Done'
            labelPosition='left'
            icon='arrow right'
            onClick={handleOk}
            positive
            disabled={isPolicyEditorLoading}
          />
        ) : (
          <>
            <Button
              content='Submit'
              labelPosition='left'
              icon='arrow right'
              onClick={handleJustificationSubmit}
              positive
              disabled={isPolicyEditorLoading}
            />
            <Button
              content='Cancel'
              onClick={handleCancel}
              icon='cancel'
              negative
              disabled={isPolicyEditorLoading}
            />
          </>
        )}
      </Modal.Actions>
    </Modal>
  )
}

export const DeleteResourceModal = () => {
  const {
    isSuccess = false,
    toggleDeleteRole = false,
    resource = {},
    setIsSuccess,
    setToggleDeleteRole,
    handleDeleteRole,
    isPolicyEditorLoading,
    setIsPolicyEditorLoading,
  } = usePolicyContext()

  const [justification, setJustification] = useState('')
  const [successAlert, setSuccessAlert] = useState(null)
  const [errorAlert, setErrorAlert] = useState(null)

  const handleDeleteSubmit = useCallback(async () => {
    setIsPolicyEditorLoading(true)
    const response = await handleDeleteRole(justification)

    if (response) {
      const { request_created, request_id, request_url } = response
      if (request_created === true) {
        setIsSuccess(true)

        setSuccessAlert({
          requestId: request_id,
          requestUrl: request_url,
        })
      } else {
        const errorMessage = `Server reported an error with the request: ${JSON.stringify(
          response
        )}`
        setErrorAlert(errorMessage)
        setIsSuccess(false)
      }
    } else {
      setErrorAlert('Failed to submit request')
      setIsSuccess(false)
    }
    setIsPolicyEditorLoading(false)
  }, [justification, handleDeleteRole, setIsPolicyEditorLoading, setIsSuccess])

  return (
    <Modal
      onClose={() => setToggleDeleteRole(false)}
      onOpen={() => setToggleDeleteRole(true)}
      open={toggleDeleteRole}
    >
      <Modal.Header>Deleting the role {resource.name}</Modal.Header>
      <Modal.Content>
        <Modal.Description>
          <Dimmer.Dimmable dimmed={isPolicyEditorLoading}>
            {!isSuccess ? (
              <>
                <p>Are you sure you want to delete this principal?</p>
                <Form>
                  <Form.TextArea
                    required
                    label='Justification'
                    placeholder='Tell us why you need this change'
                    onChange={(e) => setJustification(e.target.value)}
                    defaultValue={justification}
                  />
                </Form>
              </>
            ) : (
              <>
                {successAlert && (
                  <Message positive>
                    <Message.Header>Click below to view request</Message.Header>
                    <p>
                      <b>
                        <Link to={successAlert.requestUrl}>
                          {successAlert.requestId}
                        </Link>
                      </b>
                    </p>
                  </Message>
                )}

                {errorAlert && (
                  <Message negative>
                    <Message.Header>An Error Occured</Message.Header>
                    <p>{errorAlert}</p>
                  </Message>
                )}
              </>
            )}
            <Dimmer active={isPolicyEditorLoading} inverted>
              <Loader />
            </Dimmer>
          </Dimmer.Dimmable>
        </Modal.Description>
      </Modal.Content>
      <Modal.Actions>
        <>
          <Button
            content='Submit'
            onClick={handleDeleteSubmit}
            disabled={!(justification || '').trim() || isSuccess}
            primary
          />
          <Button onClick={() => setToggleDeleteRole(false)}>Close</Button>
        </>
      </Modal.Actions>
    </Modal>
  )
}
