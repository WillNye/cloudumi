/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { Checkbox, Message } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'
import { useHelpModal } from 'lib/hooks/useHelpModal'

export const EnablingRoleAccessAuth = ({ onChange, checked }) => {
  const { get, post } = useApi(
    'services/aws/role-access/credential-brokering',
    { shouldPersist: true }
  )

  const { error, toast, success } = useToast()

  const { QuestionMark } = useHelpModal()

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) {
      get.do().then((data) => {
        onChange(data?.state)
      })
    } else {
      onChange(get?.data?.state)
    }
  }, [])

  const handleChange = (event, { checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} Role Access Authorization`)
    post
      .do(null, action)
      .then(() => {
        onChange(checked)
        success(`Role Access Authorization is ${action}d`)
        get.do()
      })
      .catch(({ errorsMap, message }) => {
        error(errorsMap || message)
      })
  }

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
          <QuestionMark handler='aws-iam-roles' />
        </Message.Item>
        <Message.Item>
          Use the following IAM role tag values to identify users and groups
          authorized to retrieve role credentials.
        </Message.Item>
      </Message.List>
    </Message>
  )
}
