/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { Checkbox, Message } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'

export const ChallengeURLConfig = () => {
  const { get, post } = useApi('services/aws/ip-access/originauth/challenge_url')

  const { toast, success } = useToast()

  const [checked, setChecked] = useState(false)

  useEffect(
    () => get.do('enabled').then((data) => setChecked(data?.enabled)),
    []
  )

  const handleChange = (event, { name, checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} Challenge URL Config`)
    post.do(null, action).then(() => {
      setChecked(checked)
      success(`Challenge URL Config is ${action}d`)
    })
  }

  const isWorking = get?.status !== 'done' || post?.status === 'working'

  return (
    <>
      <Message>
        <Checkbox
          size='mini'
          toggle
          defaultChecked={checked}
          disabled={isWorking}
          name='challengeURLConfig'
          onChange={handleChange}
          label={{
            children: `Enabled Challenge URL Authentication`,
          }}
        />
      </Message>
    </>
  )
}
