import React, { useCallback } from 'react'
import SemanticDatepicker from 'react-semantic-ui-datepickers'

const DatePicker = ({ handleOnDateChange, isDisabled, value, inLine }) => {
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
    <div className='date-time-picker__date'>
      <SemanticDatepicker
        filterDate={(date) => {
          const now = new Date()
          return date >= now
        }}
        disabled={isDisabled}
        onChange={handleOnChange}
        type='basic'
        value={value}
        inline={inLine}
        clearable
        showToday={false}
        className='fluid'
      />
    </div>
  )
}

export default DatePicker
