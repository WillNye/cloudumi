import React, { useCallback } from 'react'
import { Dropdown } from 'semantic-ui-react'
import { HOURS, MINUTES, TIME_STATE } from '../constants'

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
        onChange={(_e, { value }) => handleOnTimeChange('minutes', value)}
        value={time.minutes}
        placeholder='Minutes'
        selection
        compact
        fluid
        options={MINUTES}
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
    </div>
  )
}

export default TimePicker
