import React, { useCallback, useEffect, useState } from 'react'
import {
  Button,
  List,
  Modal,
  Form,
  Loader,
  Dimmer,
  Segment,
  Message,
} from 'semantic-ui-react'
import { DateTime } from 'luxon'
import { Fill } from 'lib/Misc'
import { timeOptions } from './utils'
import { Link } from 'react-router-dom'
import { useAuth } from '../../../auth/AuthProviderDefault'

const TempPolicyEscalationModal = ({
  tempEscalationModalData,
  setTempEscalationModalData,
}) => {
  const [justification, setJustification] = useState('')
  const [expirationDate, setExpirationDate] = useState(timeOptions[0].value)
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
      setExpirationDate(timeOptions[0].value)
    }
  }, [tempEscalationModalData.isOpen])

  const handleSubmit = useCallback(async () => {
    if (!justification || !tempEscalationModalData.data) return

    setIsLoading(true)
    setErrorAlert(null)
    setSuccessAlert(null)

    const newExpirationDate = DateTime.utc()
      .plus({ hour: expirationDate })
      .toFormat('yyyyMMdd')

    const payload = {
      changes: {
        changes: [
          {
            principal: {
              principal_type: 'AwsResource',
              principal_arn: tempEscalationModalData.data.arn,
            },
            change_type: 'tear_can_assume_role',
          },
        ],
      },
      justification,
      expiration_date: newExpirationDate,
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
      }
      setErrorAlert(
        'Server reported an error with the request: ' + JSON.stringify(response)
      )
    } else {
      setErrorAlert('Failed to submit request')
    }

    setIsLoading(false)
  }, [tempEscalationModalData, justification, expirationDate]) // eslint-disable-line

  return (
    <Modal
      open={tempEscalationModalData.isOpen}
      size='small'
      onClose={() => setTempEscalationModalData(false)}
    >
      <Modal.Header>Temporary Escalation Access Request</Modal.Header>
      <Modal.Content>
        <Segment basic>
          <Dimmer active={isLoading} inverted>
            <Loader>Loading</Loader>
          </Dimmer>

          {tempEscalationModalData.data && (
            <>
              <Modal.Description>
                <p>
                  You are requesting temporary access to
                  <b>&nbsp;{tempEscalationModalData.data.arn}&nbsp;</b>
                  subject to the following:
                </p>

                <List bulleted>
                  <List.Item>
                    2-Factor Step-Up Authentication with Duo Verify
                  </List.Item>
                  <List.Item>
                    Approval required from account owner
                    (networking_team@example.com)
                  </List.Item>
                  <List.Item>
                    Approval required from IAM administrators
                    (iam_team@example.com)
                  </List.Item>
                  <List.Item>
                    Notification sent to security_team@example.com
                  </List.Item>
                  <List.Item>
                    Notification sent to #security-alerts Slack channel
                  </List.Item>
                  <Fill />
                </List>
                <Fill />
              </Modal.Description>

              <Form>
                <Form.Select
                  fluid
                  label='Expiration Time'
                  options={timeOptions}
                  required
                  defaultValue={timeOptions[0].value}
                  onChange={(e) => setExpirationDate(e.target.value)}
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
