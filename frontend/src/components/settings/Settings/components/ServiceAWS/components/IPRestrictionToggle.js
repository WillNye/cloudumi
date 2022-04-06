/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { Checkbox, Message } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'

export const IPRestrictionToggle = () => {
  const { get, post } = useApi('services/aws/ip-access')

  const { toast, success } = useToast()

  const [checked, setChecked] = useState(false)

  useEffect(
    () => get.do('enabled').then((data) => setChecked(data?.enabled)),
    []
  )

  const handleChange = (event, { name, checked }) => {
    const action = checked ? 'enable' : 'disable'
    toast(`Please wait, we are working to ${action} IP configuration`)
    post.do(null, action).then(() => {
      setChecked(checked)
      success(`IP configuration is ${action}d`)
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
          name='IpRanges'
          onChange={handleChange}
          label={{
            children: `Restrict brokered credentials to a set of IP ranges`,
          }}
        />
      </Message>
    </>
  )
}
