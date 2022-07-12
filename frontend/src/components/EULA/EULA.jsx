import React, { useRef } from 'react'
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

  const onScroll = () => {
    if (ref.current) {
      const { scrollTop, scrollHeight, clientHeight } = ref.current
      if (scrollTop + clientHeight === scrollHeight) {
        console.log('reached bottom')
      }
    }
  }

  return (
    <>
      <NavHeader showMenuItems={false} />
      <div className='eula'>
        <Header as='h3'>Terms of Service</Header>
        <Segment>
          <div
            onScroll={onScroll}
            ref={ref}
            style={{ height: '60vh', overflowY: 'auto' }}
          >
            {Array(30)
              .fill()
              .map((_, index) => (
                <p key={index}>{paragraph}</p>
              ))}
          </div>
        </Segment>
        <Divider horizontal />
        <Message info>
          <p>
            By clicking below, you agree to the Noq Terms and Conditons of
            Service and Privacy Policy.
          </p>
        </Message>

        <div className='eula__actions'>
          <Divider horizontal />

          <Checkbox label='Accept' />
          <Divider horizontal />
          <Button>Continue</Button>
        </div>
      </div>
    </>
  )
}

export default EULA
