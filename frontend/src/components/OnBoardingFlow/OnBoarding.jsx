import React from 'react'
import { Divider, Header, Segment } from 'semantic-ui-react'
import NavHeader from 'components/Header'
import './OnBoarding.scss'
import ConnectionMethod from './components/ConnectionMethod'
import ConfigureAccount from './components/ConfigureAccount'
import HorizontalStepper from './components/HorizontalStepper'
import CreateAWSStack from './components/CreateAWSStack/CreateAWSStack'
import CheckAccountConnection from './components/CheckAccountConnection'

const OnBoarding = () => {
  return (
    <div className='on-boarding'>
      <NavHeader showMenuItems={false} />
      <Segment basic loading={false}>
        <Header textAlign='center' as='h2'>
          Connect Noq to AWS
        </Header>
        <Divider horizontal />
        <HorizontalStepper />
        <Divider horizontal />
        <ConnectionMethod />
        <ConfigureAccount />
        <CreateAWSStack />
        <CheckAccountConnection />
      </Segment>
    </div>
  )
}

export default OnBoarding
