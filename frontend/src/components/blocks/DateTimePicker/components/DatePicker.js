import React, { useCallback } from 'react'
import SemanticDatepicker from 'react-semantic-ui-datepickers'
import { parseDate } from '../utils'

const DatePicker = ({ handleOnDateChange, isDisabled, value }) => {
  const handleOnChange = useCallback(
    (_event, data) => {
      if (!data?.value) {
        handleOnDateChange(null)
        return
      }
      handleOnDateChange(data.value)
    },
    [handleOnDateChange]
  )

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
