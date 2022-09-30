/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { Checkbox, Icon, Message, Segment } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'
import { useHelpModal } from 'lib/hooks/useHelpModal'
import { Link } from 'react-router-dom'
import { useState } from 'react'

export const EnablingTraAccessAuth = ({ setAccessData, accessData }) => {
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
          setAccessData(data)
        })
        .finally(setIsLoading(false))
    } else {
      setAccessData({
        ...accessData,
        tra_access: get?.data?.tra_access,
      })
    }
  }, [])

  const handleChange = (event, { checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} Temporary Role Access`)
    setIsLoading(true)
    post
      .do(null, action)
      .then(() => {
        setAccessData({ ...accessData, tra_access: checked })
        success(`Temporary Role Access is ${action}d`)
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
            checked={accessData?.tra_access}
            disabled={isWorking || !accessData?.role_access}
            onChange={handleChange}
            label={{
              children: 'Enabling the feature below will enable the following:',
            }}
          />
        </Message.Header>
        <Message.List>
          <Message.Item>
            Allow users to temporary escalate (or breakglass) to roles based on
            a set of contextual escalation rules&nbsp;
            <QuestionMark handler='aws-iam-roles' />
          </Message.Item>
        </Message.List>
      </Message>
    </Segment>
  )
}
