import React, { useState, useMemo, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button, Divider, Header, Icon, Segment } from 'semantic-ui-react'
import NavHeader from 'components/Header'
import ConnectionMethod from './components/ConnectionMethod'
import ConfigureAccount from './components/ConfigureAccount'
import HorizontalStepper from './components/HorizontalStepper'
import CreateAWSStack from './components/CreateAWSStack/CreateAWSStack'
import CheckAccountConnection from './components/CheckAccountConnection'
import {
  ACCOUNT_NAME_REGEX,
  MODES,
  ONBOARDING_SECTIONS,
  ONBOARDING_STEPS,
} from './constants'
import { useAuth } from 'auth/AuthProviderDefault'
import './OnBoarding.scss'

const OnBoarding = () => {
  const { CONNECTION_METHOD, CONFIGURE, CREATE_STACK, STATUS } =
    ONBOARDING_SECTIONS

  const { sendRequestCommon } = useAuth()

  const [isConnected, setIsConnected] = useState(false)
  const [activeId, setActiveId] = useState(CONNECTION_METHOD.id)
  const [accountName, setAccountName] = useState('')
  const [selectedMode, setSelectedMode] = useState(MODES.READ_WRTE)
  const [isLoading, setIsLoading] = useState(false)
  const [isHubAccount, setIsHubAccount] = useState(true)

  useEffect(() => {
    getAccountDetails()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleModeChange = (_e, { value }) => setSelectedMode(value)

  const handleAccNameChange = (e) => {
    e.preventDefault()
    const { value } = e.target
    if (ACCOUNT_NAME_REGEX.test(value)) {
      setAccountName(value)
    }
  }

  const getAccountDetails = async () => {
    setIsLoading(true)
    const resJson = await sendRequestCommon(
      null,
      `/api/v3/services/aws/account/hub`,
      'get'
    )
    if (resJson && resJson.count) {
      setIsHubAccount(false)
    }

    setIsLoading(false)
  }

  const activeSection = useMemo(() => {
    const sections = {
      [CONNECTION_METHOD.id]: <ConnectionMethod />,
      [CONFIGURE.id]: (
        <ConfigureAccount
          handleAccNameChange={handleAccNameChange}
          handleModeChange={handleModeChange}
          accountName={accountName}
          selectedMode={selectedMode}
        />
      ),
      [CREATE_STACK.id]: (
        <CreateAWSStack
          accountName={accountName}
          setIsLoading={setIsLoading}
          selectedMode={selectedMode}
          isHubAccount={isHubAccount}
        />
      ),
      [STATUS.id]: (
        <CheckAccountConnection
          setIsConnected={setIsConnected}
          isHubAccount={isHubAccount}
          accountName={accountName}
        />
      ),
    }
    return sections[activeId]
  }, [activeId, accountName, selectedMode, isHubAccount]) // eslint-disable-line react-hooks/exhaustive-deps

  const isNextDisabled = useMemo(() => {
    return activeId === CONFIGURE.id && !accountName
  }, [accountName, activeId]) // eslint-disable-line react-hooks/exhaustive-deps

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
        <Segment basic loading={isLoading}>
          <div className='on-boarding__documentation'>
            <Link to='/docs' target='_blank' rel='noopener noreferrer'>
              <Icon name='file outline' /> Documentation
            </Link>
          </div>

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
              <Button
                primary
                onClick={() => setActiveId(activeId + 1)}
                disabled={isNextDisabled}
              >
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
