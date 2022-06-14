import React, { useMemo, useState, useEffect } from 'react'
import { Icon, Step } from 'semantic-ui-react'
import { useAuth } from '../../auth/AuthProviderDefault'
import DiscoverPermissions from './components/DiscoverPermissions'
import GeneratePermissions from './components/GeneratePermissions'
import { TABS_ENUM, TIME_PER_INTERVAL } from './constants'
import './index.css'

const AutomatedPermissions = () => {
  const { sendRequestCommon } = useAuth()

  const [selectedTab, setSelectedTab] = useState(TABS_ENUM.STEP_ONE)
  const [automatedPolicy, setAutomatedpolicy] = useState({})
  const [policyRequests, setPolicyRequests] = useState([])

  useEffect(() => {
    const interval = setInterval(async () => {
      const resJson = await sendRequestCommon(
        null,
        '/api/v3/automatic_policy_request_handler/aws',
        'get'
      )

      if (resJson && resJson.count) {
        const requests = resJson.data || []
        setPolicyRequests(requests)
      } else {
        setSelectedTab(TABS_ENUM.STEP_ONE)
        setAutomatedpolicy({})
      }
    }, TIME_PER_INTERVAL)

    return () => {
      clearInterval(interval)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const renderComponent = useMemo(() => {
    if (selectedTab === TABS_ENUM.STEP_ONE) {
      return <DiscoverPermissions policyRequests={policyRequests} />
    }
    return <GeneratePermissions automatedPolicy={automatedPolicy} />
  }, [selectedTab, automatedPolicy, policyRequests])

  return (
    <div>
      <Step.Group fluid>
        <Step>
          <Icon name='assistive listening systems' color='blue' />
          <Step.Content>
            <Step.Title>Discover Permissions</Step.Title>
            <Step.Description>Listen for access denied errors</Step.Description>
          </Step.Content>
        </Step>
      </Step.Group>
      {renderComponent}
    </div>
  )
}

export default AutomatedPermissions
