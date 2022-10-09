/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { Checkbox, Icon, Message } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'
import { useHelpModal } from 'lib/hooks/useHelpModal'
import { Link } from 'react-router-dom'

export const EnablingRoleAccessAuth = ({ accessData, setAccessData }) => {
  const { get, post } = useApi(
    'services/aws/role-access/credential-brokering',
    { shouldPersist: true }
  )

  const { error, toast, success } = useToast()

  const { QuestionMark } = useHelpModal()

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) {
      get.do().then((data) => {
        setAccessData(data)
      })
    } else {
      setAccessData({
        ...accessData,
        role_access: get?.data?.role_access,
      })
    }
  }, [])

  const handleChange = (event, { checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} Role Access Authorization`)
    post
      .do(null, action)
      .then(() => {
        setAccessData({
          tra_access: checked ? accessData?.tra_access : checked,
          role_access: checked,
        })
        success(`Role Access Authorization is ${action}d`)
        get.do()
      })
      .catch(({ errorsMap, message }) => {
        error(errorsMap || message)
      })
  }

  const isWorking = get?.status !== 'done' || post?.status === 'working'

  return (
    <>
      <Message warning>
        <Message.Header>
          <Checkbox
            size='mini'
            toggle
            checked={accessData?.role_access}
            disabled={isWorking}
            onChange={handleChange}
            label={{
              children: 'Enabling the table below will enable the following:',
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
      <Message error>
        <Message.Header>
          <Icon name='warning sign'></Icon>Protect your role tags
        </Message.Header>
        <br />
        By default, Noq uses Role Tags to determine which users/groups are able
        to retrieve credentials for your various roles We strongly recommend you
        protect your role tags by restricting which roles are able to modify
        them. You can do this by adding a Service Control Policy (SCP) in your
        AWS Organizations Management Account that applies to all of the accounts
        you have deployed Noq to.
        <Link
          to={
            '/docs/getting_started/5_enable_credential_brokering/#2-enable-credential-brokering'
          }
        >
          {' '}
          Instructions are here
        </Link>
        .
      </Message>
    </>
  )
}
