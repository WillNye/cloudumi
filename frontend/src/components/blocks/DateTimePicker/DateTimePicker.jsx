import React, { useCallback, useState } from 'react'
import DatePicker from './components/DatePicker'
import RelativeRange from './components/RelativeRange'
import TimePicker from './components/TimePicker'
import { HOURS, MINUTES, TIME_STATE } from './constants'
import { convertTime12to24 } from './utils'
import './DateTimePicker.scss'

const DateTimePicker = ({
  defaultDate = null,
  isDisabled = false,
  showRelativeRange = false,
  inLine = false,
  onChange,
}) => {
  const [fullDate, setFullDate] = useState(defaultDate)
  const [time, setTime] = useState({
    hours: HOURS[11].value,
    minutes: MINUTES[0].value,
    state: TIME_STATE[1].value,
  })

  const resetTime = () => {
    setTime({
      hours: HOURS[11].value,
      minutes: MINUTES[0].value,
      state: TIME_STATE[1].value,
    })
  }

  const handleOnDateChange = useCallback(
    (newDate) => {
      resetTime()
      const currentDate = new Date()
      if (!newDate) {
        setFullDate(null)
        onChange(null)
        return
      }

      if (currentDate.getTime() >= newDate.getTime()) {
        setFullDate(defaultDate)
        onChange(defaultDate)
        return
      }
      setFullDate(newDate)
      onChange(newDate)
    },
    [defaultDate, onChange]
  )

  const handleOnTimeChange = useCallback(
    (newTime) => {
      if (!fullDate) return
      const jsDate = new Date(fullDate)
      const { hours, minutes, state } = newTime
      const timeIn24 = convertTime12to24(`${hours}:${minutes} ${state}`)
      jsDate.setHours(timeIn24.hours, timeIn24.minutes)
      setTime(newTime)
      setFullDate(jsDate)
      onChange(jsDate)
    },
    [fullDate, onChange]
  )

  return (
    <div className='date-time-picker'>
      {showRelativeRange && (
        <div className='date-time-picker__container'>
          <RelativeRange />
        </div>
      )}
      <div className='date-time-picker__container'>
        <DatePicker
          handleOnDateChange={handleOnDateChange}
          isDisabled={isDisabled}
          value={defaultDate}
          inLine={inLine}
        />
        {fullDate && (
          <TimePicker
            onTimeChange={handleOnTimeChange}
            isDisabled={isDisabled}
            time={time}
          />
        )}
      </div>
    </div>
  )
}

export default DateTimePicker
