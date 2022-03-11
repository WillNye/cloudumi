/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { Button, Checkbox, Message } from 'semantic-ui-react'
import { useApi } from 'hooks/useApi'
import { useToast } from 'lib/Toast'

export const IPRestrictionToggle = ({ onChange, checked }) => {

  const { get, post } = useApi('services/aws/ip-access/enable') // TODO: Replace after sync with Matt

  const { toast, success } = useToast()

  // useEffect(() => get.do().then(onChange), [])

  const handleChange = (event, { name, checked }) => {
    console.log(name, checked)
    // const action = checked ? 'enable' : 'disable'
    // toast(`Please wait, we are working to ${action} IP configuration`)
    // post.do(null, action).then(() => {
    //   success(`IP configuration is ${action}d`)
    //   onChange(checked)
    // })
  }

  const handleHelpModal = (handler) => {}

  const isWorking = get?.status !== 'done' || post?.status === 'working'

  return (
    <>
      {/* <Message>
        <Checkbox
          size='mini'
          toggle
          checked={checked}
          // disabled={isWorking}
          name="requestersIpAddress"
          onChange={handleChange}
          label={{
            children:
              `Restrict brokered credentials to requester's IP address`,
          }}
        />
      </Message> */}
      <Message>
        <Checkbox
          size='mini'
          toggle
          checked={checked}
          // disabled={isWorking}
          name="IpRanges"
          onChange={handleChange}
          label={{
            children:
              `Restrict brokered credentials to a set of IP ranges`,
          }}
        />
      </Message>
    </>
  )
}
