/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { Checkbox, Icon, Message, Segment } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'
import { useHelpModal } from 'lib/hooks/useHelpModal'
import { Link } from 'react-router-dom'
import { useState } from 'react'

export const EnablingTraAccessAuth = () => {
  const [checked, setChecked] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const { get, post } = useApi('services/aws/tra-access/credential-brokering', {
    shouldPersist: true,
  })

  const { error, toast, success } = useToast()

  const { QuestionMark } = useHelpModal()

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) {
      setIsLoading(true)
      get
        .do()
        .then((data) => {
          setChecked(data?.tra_access)
        })
        .finally(setIsLoading(false))
    } else {
      setChecked(get?.data?.tra_access)
    }
  }, [])

  const handleChange = (event, { checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} Role Access Authorization`)
    setIsLoading(true)
    post
      .do(null, action)
      .then(() => {
        setChecked(checked)
        success(`Tra Access Authorization is ${action}d`)
        get.do()
      })
      .catch(({ errorsMap, message }) => {
        error(errorsMap || message)
      })
      .finally(setIsLoading(false))
  }

  const isWorking = get?.status !== 'done' || post?.status === 'working'

  return (
    <Segment basic loading={isLoading}>
      <Message warning>
        <Message.Header>
          <Checkbox
            size='mini'
            toggle
            checked={checked}
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
    </Segment>
  )
}
