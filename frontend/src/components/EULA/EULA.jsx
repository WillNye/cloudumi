import React, { useRef, useState } from 'react'
import {
  Button,
  Checkbox,
  Divider,
  Header,
  Message,
  Segment,
} from 'semantic-ui-react'
import NavHeader from '../Header'
import { paragraph } from './mockData'
import './eula.css'

const EULA = () => {
  const ref = useRef()

  const [hasViewedAgreement, setHasViewedAgreement] = useState(false)
  const [acceptAgreement, setAcceptAgreemnet] = useState(false)

  const onScroll = () => {
    if (ref.current) {
      const { scrollTop, scrollHeight, clientHeight } = ref.current
      if (scrollTop + clientHeight === scrollHeight) {
        setHasViewedAgreement(true)
      }
    }
  }

  return (
    <>
      <NavHeader showMenuItems={false} />
      <div className='eula'>
        <Header as='h3'>Terms of Service</Header>
        <Segment>
          <div onScroll={onScroll} ref={ref} className='eula__documnet'>
            {Array(30)
              .fill()
              .map((_, index) => (
                <p key={index}>{paragraph}</p>
              ))}
          </div>
        </Segment>

        <Divider horizontal />
        <Divider horizontal />

        <div className='eula__actions'>
          <p>
            By clicking below, you agree to the Noq Terms and Conditons of
            Service and Privacy Policy.
          </p>
        </div>

        <Divider horizontal />

        <div className='eula__actions'>
          <Checkbox
            label='Accept'
            onChange={(_event, data) => setAcceptAgreemnet(data.checked)}
            checked={acceptAgreement}
            disabled={!hasViewedAgreement}
          />
        </div>

        <Divider horizontal />

        <div className='eula__actions'>
          <Button
            className='eula__buttton'
            primary
            fluid
            disabled={!acceptAgreement}
          >
            Continue
          </Button>
        </div>
      </div>
    </>
  )
}

export default EULA
