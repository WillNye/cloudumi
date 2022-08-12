import React, { useMemo, useState } from 'react'
import { Checkbox, Divider, Segment } from 'semantic-ui-react'
import { formatISODate } from '../../utils'
import './VerticalStepper.scss'

const VerticalStepper = (props) => {
  const {
    resourceHistory,
    handleVersionChange,
    resourceArn,
    diffChanges,
    handleAssociatedHistoryChange,
    associatedHistoryChange,
  } = props

  const [showAssociatedPolicy, setShowAssociatedPolicy] = useState(true)

  const filteredResourceHistory = useMemo(() => {
    if (showAssociatedPolicy) {
      return resourceHistory
    }
    return resourceHistory.filter(
      (version) => version.config_change.arn === resourceArn
    )
  }, [showAssociatedPolicy, resourceHistory, resourceArn])

  const activeElementIds = useMemo(() => {
    const { oldVersion, newVersion } = diffChanges
    const activeIds = []
    if (oldVersion) {
      activeIds.push(oldVersion.updated_at)
    }
    if (newVersion) {
      activeIds.push(newVersion.updated_at)
    }
    if (associatedHistoryChange) {
      activeIds.push(associatedHistoryChange.updated_at)
    }
    return activeIds
  }, [diffChanges, associatedHistoryChange])

  return (
    <div className='vertical-stepper'>
      <h4>All times are in UTC</h4>

      <Divider horizontal />

      <Checkbox
        toggle
        checked={showAssociatedPolicy}
        onChange={(e, data) => setShowAssociatedPolicy(data.checked)}
        label='View associated policy changes '
      />

      <Divider horizontal />

      <div className='steps'>
        {filteredResourceHistory.map((version, index) => {
          const isActive = activeElementIds.includes(version.updated_at)
          return resourceArn === version.config_change.arn ? (
            <div
              className={`${isActive ? 'steps__step__active' : 'steps__step'}`}
              key={index}
            >
              <div
                className={`steps__step-header ${isActive && 'steps__active'}`}
                onClick={() => handleVersionChange(version)}
              >
                <div className='steps__header'>
                  {formatISODate(version.updated_at)}
                </div>
                <div className='steps__subheader'>
                  {version.config_change.resourceName}
                </div>
              </div>
            </div>
          ) : (
            <div
              className={`${
                activeElementIds.includes(version.updated_at)
                  ? 'steps__step__active'
                  : 'steps__step'
              }`}
              key={index}
            >
              <div
                className='steps__step-header'
                onClick={() => handleAssociatedHistoryChange(version)}
              >
                <div className='steps__subheader'>Associated policy change</div>
                <Segment
                  className={`steps__step-header ${
                    isActive && 'steps__active'
                  }`}
                >
                  <div className='steps__header'>
                    {formatISODate(version.updated_at)}
                  </div>
                  <div className='steps__subheader'>
                    {version.config_change.resourceName}
                  </div>
                </Segment>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default VerticalStepper
