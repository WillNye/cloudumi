import React, { useMemo, useState, useEffect } from 'react'
import { DateTime } from 'luxon'
import { useAuth } from '../../auth/AuthProviderDefault'
import DiscoverPermissions from './components/DiscoverPermissions'
import GeneratePermissions from './components/GeneratePermissions'
import Tabs from './components/Tabs'
import {
  TABS_ENUM,
  APPLIED_POLICY_STATUSES,
  TIME_PER_INTERVAL,
} from './constants'
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
        const policyRequests = (resJson.data || []).filter(
          ({ last_updated, status }) => {
            const lastUpdated = DateTime.fromISO(last_updated)
            const currentTime = DateTime.utc().minus({ seconds: 10 })
            const hasExpired = lastUpdated < currentTime

            if (hasExpired && APPLIED_POLICY_STATUSES.includes(status)) {
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
    }, TIME_PER_INTERVAL)

    return () => {
      clearInterval(interval)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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
