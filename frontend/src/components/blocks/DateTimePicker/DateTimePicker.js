import React, { useCallback, useState } from 'react'
import { Button, Divider } from 'semantic-ui-react'
import DatePicker from './components/DatePicker'
import TimePicker from './components/TimePicker'
import './DateTimePicker.scss'

const DateTimePicker = ({ defaultDate, onSubmit, isDisabled = false }) => {
  const [fullDate, setFullDate] = useState(defaultDate)
  const [time, setTime] = useState()
  const [date, setDate] = useState()

  const handleOnDateChange = useCallback(
    (newDate) => {
      const currentDate = new Date()
      if (!newDate) {
        setFullDate(null)
        return
      }

      if (currentDate.getTime() >= newDate.getTime()) {
        setFullDate(defaultDate)
        return
      }

      setFullDate(newDate)
    },
    [time, defaultDate]
  )

  const handleOnTimeChange = useCallback(
    (newTime) => {
      setFullDate(newTime)
    },
    [date]
  )

  const handleOnSubmit = useCallback(() => {
    onSubmit && onSubmit(fullDate)
  }, [fullDate])

  return (
    <div>
      <DatePicker
        handleOnDateChange={handleOnDateChange}
        isDisabled={isDisabled}
        value={defaultDate}
      />
      <Divider horizontal />
      <TimePicker
        handleOnTimeChange={handleOnTimeChange}
        isDisabled={isDisabled || !fullDate}
      />
      <Divider horizontal />
      <Button onClick={() => handleOnSubmit(fullDate)} disabled={isDisabled}>
        Submit
      </Button>
    </div>
  )
}

export default DateTimePicker
