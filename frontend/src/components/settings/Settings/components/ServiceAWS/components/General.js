import React from 'react'
// import { Checkbox, Message } from 'semantic-ui-react'
import { CIDRBlock } from './CIDRBlock'
import { IPRestrictionToggle } from './IPRestrictionToggle'

export const General = () => {
  return (
    <>
      {/* <Message>
        <Checkbox
          size='mini'
          toggle
          name='requestersIpAddress'
          // onChange={handleChange} // Need endpoint for that
          label={{
            children: `Automatically update role trust policies when an authorized user
              requests credentials, but Noq isn't authorized to perform the role
              assumption.`,
          }}
        />
      </Message> */}

      <IPRestrictionToggle />

      <CIDRBlock />
    </>
  )
}
