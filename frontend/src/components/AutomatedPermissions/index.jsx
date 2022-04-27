import React, { useMemo, useState, useEffect } from 'react'
import { DateTime } from 'luxon'
import { useAuth } from '../../auth/AuthProviderDefault'
import DiscoverPermissions from './components/DiscoverPermissions'
import GeneratePermissions from './components/GeneratePermissions'
import Tabs from './components/Tabs'
import { TABS_ENUM } from './constants'
import './index.css'

const expiredStatuses = [
  'applied_awaiting_execution',
  'applied_and_success',
  'applied_and_failure',
]

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
        const policyRequests = (resJson.data || []).filter(
          ({ last_updated, status }) => {
            const lastUpdated = DateTime.fromISO(last_updated)
            const currentTime = DateTime.utc().minus({ seconds: 30 })
            const hasExpired = lastUpdated < currentTime

            if (hasExpired && expiredStatuses.includes(status)) {
              return false
            }
            return true
          }
        )

        if (policyRequests.length) {
          setAutomatedpolicy(policyRequests[0])
          setSelectedTab(TABS_ENUM.STEP_TWO)
        } else {
          setSelectedTab(TABS_ENUM.STEP_ONE)
          setAutomatedpolicy({})
        }
      } else {
        setSelectedTab(TABS_ENUM.STEP_ONE)
        setAutomatedpolicy({})
      }
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
  }, [selectedTab, automatedPolicy])

  return (
    <div>
      <Tabs selectedTab={selectedTab} />
      {renderComponent}
    </div>
  )
}

export default AutomatedPermissions
