/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { Button, Checkbox, Message } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'

export const EnablingRoleAccessAuth = ({ onChange, checked }) => {
  const { get, post } = useApi('services/aws/role-access/credential-brokering')

  const { toast, success } = useToast()

  useEffect(
    () =>
      get.do().then((res) => {
        onChange(res?.state)
      }),
    []
  )

  const handleChange = (event, { checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} Role Access Authorization`)
    post.do(null, action).then(() => {
      success(`Role Access Authorization is ${action}d`)
      onChange(checked)
    })
  }

  const handleHelpModal = (handler) => {}

  const isWorking = get?.status !== 'done' || post?.status === 'working'

  return (
    <Message warning>
      <Message.Header>
        <Checkbox
          size='mini'
          toggle
          checked={checked}
          disabled={isWorking}
          onChange={handleChange}
          label={{
            children:
              'Enabling the table below you agree with the following rules:',
          }}
        />
      </Message.Header>
      <Message.List>
        <Message.Item>
          Broker temporary credentials to AWS IAM roles.&nbsp;
          <Button
            size='mini'
            circular
            icon='question'
            basic
            onClick={() => handleHelpModal('aws-iam-roles')}
          />
        </Message.Item>
        <Message.Item>
          Use the following IAM role tag values to identify users and groups
          authorized to retrieve role credentials.
        </Message.Item>
      </Message.List>
    </Message>
  )
}
