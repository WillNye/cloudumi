import React, { useMemo, useState } from 'react'
import DiscoverPermissions from './components/DiscoverPermissions'
import GeneratePermissions from './components/GeneratePermissions'
import Tabs from './components/Tabs'
import { TABS_ENUM } from './constants'
import './index.css'

const AutomatedPermissions = () => {
  const [selectedTab, setSelectedTab] = useState(TABS_ENUM.STEP_ONE)

  const renderComponent = useMemo(() => {
    if (selectedTab === TABS_ENUM.STEP_ONE) {
      return <DiscoverPermissions />
    }
    return <GeneratePermissions />
  }, [selectedTab])

  return (
    <div>
      <Tabs selectedTab={selectedTab} setSelectedTab={setSelectedTab} />
      {renderComponent}
    </div>
  )
}

export default AutomatedPermissions
