import React from 'react'
import SemanticDatepicker from 'react-semantic-ui-datepickers'
import { parseDate } from '../utils'

const DatePicker = ({ setDate, isDisabled, value }) => {
  const handleOnChange = (_event, data) => {
    if (!data?.value) {
      setDate(null)
      return
    }
    setDate(data.value)
  }

  return (
    <SemanticDatepicker
      filterDate={(date) => {
        const now = new Date()
        return date >= now
      }}
      disabled={isDisabled}
      onChange={handleOnChange}
      type='basic'
      value={parseDate(value)}
      compact
    />
  )
}

export default DatePicker
