import React, { useCallback, useState } from 'react'
import DatePicker from './components/DatePicker'
import RelativeRange from './components/RelativeRange'
import TimePicker from './components/TimePicker'
import { getDefaultTime, setNewDateTime } from './utils'
import './DateTimePicker.scss'

const DateTimePicker = ({
  defaultTimeInSeconds = null,
  defaultDate = null,
  isDisabled = false,
  showRelativeRange = false,
  showDateSelector = true,
  inLine = false,
  onDateSelectorChange,
  onRelativeTimeChange,
}) => {
  const [fullDate, setFullDate] = useState(defaultDate)
  const [time, setTime] = useState(getDefaultTime(defaultDate))

  const resetTime = () => {
    setTime(getDefaultTime())
  }

  const handleOnDateChange = useCallback(
    (newDate) => {
      const currentDate = new Date()
      if (!newDate) {
        setFullDate(null)
        onDateSelectorChange(null)
        resetTime()
        return
      }

      if (currentDate.getTime() >= newDate.getTime()) {
        setFullDate(fullDate)
        onDateSelectorChange(fullDate)
        return
      }
      const dateTime = time ? time : getDefaultTime(fullDate || newDate)
      const newJsDate = setNewDateTime(newDate, dateTime)
      setFullDate(newJsDate)
      setTime(dateTime)
      onDateSelectorChange(newJsDate)
    },
    [fullDate, time, onDateSelectorChange]
  )

  const handleOnTimeChange = useCallback(
    (newTime) => {
      if (!fullDate) return
      const newDate = setNewDateTime(fullDate, newTime)
      setTime(newTime)
      setFullDate(newDate)
      onDateSelectorChange(newDate)
    },
    [fullDate, onDateSelectorChange]
  )

  return (
    <div className='date-time-picker'>
      {showRelativeRange && (
        <div className='date-time-picker__relative-time'>
          <RelativeRange
            onChange={onRelativeTimeChange}
            defaultTimeInSeconds={defaultTimeInSeconds}
          />
        </div>
      )}
      {showDateSelector && (
        <div className='date-time-picker__input-width'>
          <DatePicker
            handleOnDateChange={handleOnDateChange}
            isDisabled={isDisabled}
            value={defaultDate}
            inLine={inLine}
          />
          {fullDate && time && (
            <TimePicker
              onTimeChange={handleOnTimeChange}
              isDisabled={isDisabled}
              time={time}
            />
          )}
        </div>
      )}
    </div>
  )
}

export default DateTimePicker
