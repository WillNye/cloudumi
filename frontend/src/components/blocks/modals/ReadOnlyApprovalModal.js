import React, { useCallback, useState } from 'react'
import { Modal, Form, Button, Segment, Divider } from 'semantic-ui-react'

const ReadOnlyApprovalModal = ({
  isApprovalModalOpen,
  setIsApprovalModalOpen,
  onSubmitChange,
}) => {
  const [accessKeyId, setAccessKeyId] = useState('')
  const [secretAccessKey, setSecretAccessKey] = useState('')
  const [sessionToken, setSessionToken] = useState('')

  const resetState = () => {
    setAccessKeyId('')
    setSecretAccessKey('')
    setSessionToken('')
  }

  const handleApplyChanges = useCallback(() => {
    if (accessKeyId && secretAccessKey) {
      const data = {
        aws_access_key_id: accessKeyId,
        aws_secret_access_key: secretAccessKey,
        aws_session_token: sessionToken || null,
      }
      setIsApprovalModalOpen(false)
      onSubmitChange(data)
      resetState()
    }
  }, [accessKeyId, secretAccessKey, sessionToken]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Modal
      open={isApprovalModalOpen}
      size='small'
      onClose={() => setIsApprovalModalOpen(false)}
    >
      <Modal.Header>Change affects a read-only account</Modal.Header>
      <Modal.Content>
        <Segment basic>
          <p>
            It looks like you are trying to apply a change to an account that
            Noq only has read access to.
          </p>
          <p>
            Please provide one-time-use credentials with the appropriate
            permissions for Noq to apply this change, or apply the change
            manually and mark the change as approved
          </p>

          <Form onSubmit={handleApplyChanges}>
            <Form.Input
              fuild
              required
              placeholder='Access Key ID'
              value={accessKeyId}
              onChange={(event) => setAccessKeyId(event.target.value)}
            />
            <Form.Input
              fuild
              required
              placeholder='Secret Access Key'
              value={secretAccessKey}
              onChange={(event) => setSecretAccessKey(event.target.value)}
            />
            <Form.Input
              fuild
              placeholder='Session Token'
              value={sessionToken}
              onChange={(event) => setSessionToken(event.target.value)}
            />

            <Button.Group>
              <Button positive type='submit'>
                Apply change with one-time credentials
              </Button>
              <Button.Or />
              <Button
                onClick={() => {
                  setIsApprovalModalOpen(false)
                  resetState()
                  onSubmitChange()
                }}
                positive
              >
                Just Mark mark the change as approved
              </Button>
            </Button.Group>
          </Form>
          <Divider horizontal />
        </Segment>
      </Modal.Content>

      <Modal.Actions>
        <Button
          negative
          onClick={() => {
            resetState()
            setIsApprovalModalOpen(false)
          }}
        >
          Close
        </Button>
      </Modal.Actions>
    </Modal>
  )
}

export default ReadOnlyApprovalModal
