import React, { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Modal,
  Form,
  Loader,
  Dimmer,
  Segment,
  Message,
} from 'semantic-ui-react'
import { Fill } from 'lib/Misc'
import { TIME_OPTIONS } from './utils'
import { Link } from 'react-router-dom'
import { useAuth } from '../../../auth/AuthProviderDefault'

const TempPolicyEscalationModal = ({
  tempEscalationModalData,
  setTempEscalationModalData,
}) => {
  const [justification, setJustification] = useState('')
  const [timeInSeconds, setTimeInSeconds] = useState(TIME_OPTIONS[0].value)
  const [isLoading, setIsLoading] = useState(false)
  const [errorAlert, setErrorAlert] = useState(null)
  const [successAlert, setSuccessAlert] = useState(null)

  const { sendRequestCommon } = useAuth()

  useEffect(() => {
    if (!tempEscalationModalData.isOpen) {
      setErrorAlert(null)
      setSuccessAlert(null)
      setIsLoading(false)
      setJustification('')
      setTimeInSeconds(TIME_OPTIONS[0].value)
    }
  }, [tempEscalationModalData.isOpen])

  const handleSubmit = useCallback(async () => {
    if (!justification || !tempEscalationModalData.data) return

    setIsLoading(true)
    setErrorAlert(null)
    setSuccessAlert(null)

    const payload = {
      changes: {
        changes: [
          {
            principal: {
              principal_type: 'AwsResource',
              principal_arn: tempEscalationModalData.data.arn,
            },
            change_type: 'tra_can_assume_role',
          },
        ],
      },
      justification,
      ttl: timeInSeconds,
      dry_run: false,
      admin_auto_approve: false,
    }

    const response = await sendRequestCommon(payload, '/api/v2/request')

    if (response) {
      const { request_created, request_id, request_url } = response
      if (request_created === true) {
        setSuccessAlert({
          requestId: request_id,
          requestUrl: request_url,
        })
      } else {
        setErrorAlert(
          'Server reported an error with the request: ' +
            JSON.stringify(response)
        )
      }
    } else {
      setErrorAlert('Failed to submit request')
    }

    setIsLoading(false)
  }, [tempEscalationModalData, justification, timeInSeconds]) // eslint-disable-line

  return (
    <Modal
      open={tempEscalationModalData.isOpen}
      size='small'
      onClose={() => setTempEscalationModalData(false)}
    >
      <Modal.Header>Temporary Role Access Request</Modal.Header>
      <Modal.Content>
        <Segment basic>
          <Dimmer active={isLoading} inverted>
            <Loader>Loading</Loader>
          </Dimmer>

          {tempEscalationModalData.data && (
            <>
              <Modal.Description>
                <p>
                  You are requesting temporary access to: <br />
                  <b>&nbsp;{tempEscalationModalData.data.arn}&nbsp;</b>.
                </p>
                <p>
                  Your request will be routed to the appropriate approvers,
                  or self-approved based on the Temporary Role Access rules
                  that your organization has configured. More information is
                  available in our {' '}
                  <a href='/docs/features/permissions_management_and_request_framework/temporary_role_access/'>
                    documentation
                  </a>.
                </p>
                <Fill />
              </Modal.Description>

              <Form>
                <Form.Select
                  fluid
                  label='Expiration Time'
                  options={TIME_OPTIONS}
                  required
                  defaultValue={TIME_OPTIONS[0].value}
                  onChange={(_e, { value }) => setTimeInSeconds(value)}
                  disabled={!!successAlert}
                />
                <Fill />

                <Form.TextArea
                  label='Justification'
                  placeholder='Reason for requesting access'
                  style={{ width: 'fluid' }}
                  required
                  disabled={!!successAlert}
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                />
              </Form>

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
        </Segment>
      </Modal.Content>

      <Modal.Actions>
        <Button
          onClick={() => setTempEscalationModalData(false)}
          disabled={isLoading}
        >
          Close
        </Button>

        <Button
          onClick={handleSubmit}
          color='red'
          disabled={!tempEscalationModalData.data || isLoading || successAlert}
        >
          Request Access
        </Button>
      </Modal.Actions>
    </Modal>
  )
}

export default TempPolicyEscalationModal
