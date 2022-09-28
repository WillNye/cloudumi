import React, { useCallback } from 'react'
import { Dropdown } from 'semantic-ui-react'
import { HOURS, TIME_STATE } from '../constants'
import { getUserTimeZone } from '../utils'

const TIME_ZONE = getUserTimeZone()

const TimePicker = ({ onTimeChange, isDisabled, time }) => {
  const handleOnTimeChange = useCallback(
    (name, value) => {
      onTimeChange({ ...time, [name]: value })
    },
    [time, onTimeChange]
  )

  return (
    <div className='date-time-picker__time'>
      <Dropdown
        onChange={(_e, { value }) => handleOnTimeChange('hours', value)}
        placeholder='Hours'
        value={time.hours}
        selection
        compact
        fluid
        options={HOURS}
        disabled={isDisabled}
      />
      <Dropdown
        value={time.state}
        onChange={(_e, { value }) => handleOnTimeChange('state', value)}
        placeholder='State'
        selection
        compact
        fluid
        options={TIME_STATE}
        disabled={isDisabled}
      />
      <p className='date-time-picker__time-text'>{TIME_ZONE}</p>
    </div>
  )
}

export default TimePicker
