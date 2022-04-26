import React, { useMemo, useState, useEffect } from 'react'
import { useAuth } from '../../auth/AuthProviderDefault'
import DiscoverPermissions from './components/DiscoverPermissions'
import GeneratePermissions from './components/GeneratePermissions'
import Tabs from './components/Tabs'
import { TABS_ENUM } from './constants'
import './index.css'

const AutomatedPermissions = () => {
  const { sendRequestCommon } = useAuth()

  const [selectedTab, setSelectedTab] = useState(TABS_ENUM.STEP_ONE)
  const [automatedPolicy, setAutomatedpolicy] = useState({})

  useEffect(() => {
    const interval = setInterval(async () => {
      const resJson = await sendRequestCommon(
        null,
        '/api/v3/automatic_policy_request_handler/aws',
        'get'
      )

      if (resJson && resJson.count) {
        setAutomatedpolicy(resJson.data[0])
        setSelectedTab(TABS_ENUM.STEP_TWO)
      } else {
        setSelectedTab(TABS_ENUM.STEP_ONE)
      }
      console.log('----------', resJson)
    }, 5000)

    return () => {
      clearInterval(interval)
    }
  }, [])

  const renderComponent = useMemo(() => {
    if (selectedTab === TABS_ENUM.STEP_ONE) {
      return <DiscoverPermissions />
    }
    return <GeneratePermissions automatedPolicy={automatedPolicy} />
  }, [selectedTab])

  return (
    <div>
      <Tabs selectedTab={selectedTab} />
      {renderComponent}
    </div>
  )
}

export default AutomatedPermissions
