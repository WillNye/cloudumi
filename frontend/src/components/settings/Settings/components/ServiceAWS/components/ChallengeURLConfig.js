/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { Checkbox, Message } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'

export const ChallengeURLConfig = () => {
  const { get, post } = useApi('auth/challenge_url', { shouldPersist: true })

  const { error, toast, success } = useToast()

  const [checked, setChecked] = useState(false)

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) {
      get.do().then((data) => {
        setChecked(data?.enabled)
      })
    } else {
      setChecked(get?.data?.enabled)
    }
  }, [])

  const handleChange = (event, { name, checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} Challenge URL Config`)
    console.log(checked)
    post
      .do({ enabled: checked })
      .then(() => {
        setChecked(checked)
        success(`Challenge URL Config is ${action}d`)
        get.do()
      })
      .catch(({ errorsMap, message }) => {
        error(errorsMap || message)
      })
  }

  const isWorking = get?.status !== 'done' || post?.status === 'working'

  return (
    <>
      <Message>
        <Checkbox
          size='mini'
          toggle
          checked={checked}
          disabled={isWorking}
          name='challengeURLConfig'
          onChange={handleChange}
          label={{
            children: `Enable Challenge URL Authentication`,
          }}
        />
      </Message>
    </>
  )
}
