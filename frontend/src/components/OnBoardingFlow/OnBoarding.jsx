import React, { useState, useMemo } from 'react'
import { Button, Divider, Header, Icon, Segment } from 'semantic-ui-react'
import NavHeader from 'components/Header'
import ConnectionMethod from './components/ConnectionMethod'
import ConfigureAccount from './components/ConfigureAccount'
import HorizontalStepper from './components/HorizontalStepper'
import CreateAWSStack from './components/CreateAWSStack/CreateAWSStack'
import CheckAccountConnection from './components/CheckAccountConnection'
import { ONBOARDING_SECTIONS, ONBOARDING_STEPS } from './constants'
import { Link } from 'react-router-dom'
import './OnBoarding.scss'

const OnBoarding = () => {
  const { CONNECTION_METHOD, CONFIGURE, CREATE_STACK, STATUS } =
    ONBOARDING_SECTIONS

  const [isConnected, setIsConnected] = useState(false)
  const [activeId, setActiveId] = useState(CONNECTION_METHOD.id)

  const activeSection = useMemo(() => {
    const sections = {
      [CONNECTION_METHOD.id]: <ConnectionMethod />,
      [CONFIGURE.id]: <ConfigureAccount />,
      [CREATE_STACK.id]: <CreateAWSStack />,
      [STATUS.id]: <CheckAccountConnection setIsConnected={setIsConnected} />,
    }
    return sections[activeId]
  }, [activeId]) // eslint-disable-line react-hooks/exhaustive-deps

  const connectedComponet = (
    <div className='connecting-account'>
      <Divider horizontal />
      <Icon color='green' name='check circle' size='huge' />
      <Divider horizontal />
      <Divider horizontal />
      <div>
        <Header as='h3'>
          <Icon color='green' name='check circle outline' size='small' />
          <Header.Content>
            Onboarding account
            <Header.Subheader>
              Complete. You can view your account details in{' '}
              <Link to='/settings'>Settings.</Link>
            </Header.Subheader>
          </Header.Content>
        </Header>
        <Divider horizontal />
        <Divider horizontal />
        <Header as='h3'>
          <Icon name='cloud download' color='blue' />
          <Header.Content>
            Caching resources
            <Header.Subheader>
              Started caching resources (This may take a while)
            </Header.Subheader>
          </Header.Content>
        </Header>
      </div>
    </div>
  )

  return (
    <div className='on-boarding'>
      <NavHeader showMenuItems={false} />
      {isConnected ? (
        connectedComponet
      ) : (
        <Segment basic loading={false}>
          <Header textAlign='center' as='h2'>
            Connect Noq to AWS
          </Header>
          <Divider horizontal />
          <HorizontalStepper activeId={activeId} steps={ONBOARDING_STEPS} />
          <Divider horizontal />
          <Divider horizontal />
          {activeSection}
          <Divider horizontal />
          <div className='on-boarding__actions'>
            {activeId !== CONNECTION_METHOD.id && (
              <Button onClick={() => setActiveId(activeId - 1)}>Back</Button>
            )}
            {activeId !== STATUS.id && (
              <Button primary onClick={() => setActiveId(activeId + 1)}>
                Next
              </Button>
            )}
          </div>
        </Segment>
      )}
    </div>
  )
}

export default OnBoarding
