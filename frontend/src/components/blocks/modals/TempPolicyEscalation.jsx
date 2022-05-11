import React from 'react'
import { Button, List, Modal, Form } from 'semantic-ui-react'
import { Fill } from 'lib/Misc'
import { timeOptions } from './utils'

const TempPolicyEscalationModal = ({
  isTempEscalationModalOpen,
  setIsTempEscalationModalOpen,
}) => {
  return (
    <Modal
      open={isTempEscalationModalOpen}
      size='small'
      onClose={() => setIsTempEscalationModalOpen(false)}
    >
      <Modal.Header>Temporary Escalation Access Request</Modal.Header>
      <Modal.Content>
        <Modal.Description>
          <p>
            You are requesting temporary access to
            arn:aws:iam::385817472833:role/admin. This request will be be
            subject to the following:
          </p>

          <List bulleted>
            <List.Item>
              2-Factor Step-Up Authentication with Duo Verify
            </List.Item>
            <List.Item>
              Approval required from account owner (networking_team@example.com)
            </List.Item>
            <List.Item>
              Approval required from IAM administrators (iam_team@example.com)
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
            defaultValue={timeOptions[0].value}
          />
          <Fill />

          <Form.TextArea
            label='Justification'
            placeholder='Reason for requesting access'
            style={{ width: 'fluid' }}
            onChange={(e) => {}}
          />
        </Form>
      </Modal.Content>
      <Modal.Actions>
        <Button onClick={() => setIsTempEscalationModalOpen(false)}>
          Cancel
        </Button>

        <Button onClick={() => setIsTempEscalationModalOpen(false)} color='red'>
          Request Access
        </Button>
      </Modal.Actions>
    </Modal>
  )
}

export default TempPolicyEscalationModal
