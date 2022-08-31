import React, { useEffect, useState } from 'react'
import { Dropdown } from 'semantic-ui-react'
import { HOURS, MINUTES, TIME_STATE } from '../constants'
import { convertTime12to24 } from '../utils'

const TimePicker = ({ handleOnTimeChange, isDisabled }) => {
  const [hours, setHours] = useState(HOURS[11].value)
  const [minutes, setMinutes] = useState(MINUTES[0].value)
  const [timeState, setTimeState] = useState(TIME_STATE[0].value)

  useEffect(() => {
    const timeIn24 = convertTime12to24(`${hours}:${minutes} ${timeState}`)
    handleOnTimeChange(timeIn24)
  }, [hours, minutes, timeState, handleOnTimeChange])

  return (
    <div>
      <Dropdown
        onChange={(_e, { value }) => setHours(value)}
        placeholder='Hours'
        value={hours}
        selection
        compact
        options={HOURS}
        disabled={isDisabled}
      />
      <Dropdown
        onChange={(_e, { value }) => {
          setMinutes(value)
        }}
        value={minutes}
        placeholder='Minutes'
        compact
        selection
        options={MINUTES}
        disabled={isDisabled}
      />
      <Dropdown
        value={timeState}
        onChange={(_e, { value }) => setTimeState(value)}
        placeholder='State'
        compact
        selection
        options={TIME_STATE}
        disabled={isDisabled}
      />
    </div>
  )
}

export default TimePicker
