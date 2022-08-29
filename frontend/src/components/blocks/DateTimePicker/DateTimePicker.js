import React from 'react'
import DatePicker from './components/DatePicker'
import TimePicker from './components/TimePicker'
import './DateTimePicker.scss'

const DateTimePicker = () => {
  return (
    <div>
      <DatePicker />
      <TimePicker />
    </div>
  )
}

export default DateTimePicker
