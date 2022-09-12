import React from 'react'
import { Divider, Header, Segment } from 'semantic-ui-react'
import NavHeader from 'components/Header'
import ConnectAWS from './components/ConnectAWS'
import './OnBoarding.scss'
import ConnectionMethod from './components/ConnectionMethod'
import ConfigureAccount from './components/ConfigureAccount'

const OnBoarding = () => {
  return (
    <div className='on-boarding'>
      <NavHeader showMenuItems={false} />
      <Segment basic loading={false}>
        <Header as='h2'>Connect Noq to AWS</Header>
        <Divider horizontal />
        <div className='on-boarding__container'>
          {/* <ConnectionMethod /> */}
          <ConfigureAccount />
          {/* <ConnectAWS /> */}
        </div>
      </Segment>
    </div>
  )
}

export default OnBoarding
