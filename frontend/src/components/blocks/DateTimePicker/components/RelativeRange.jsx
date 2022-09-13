import React from 'react'
import { useCallback } from 'react'
import { useState } from 'react'
import { Form, Input, Select } from 'semantic-ui-react'
import { RELATIVE_TIME_RANGE_TYPES } from '../constants'
import { getRelativeTimeFromSeconds, getTimeFromRelativeObject } from '../utils'

const RelativeRange = ({
  defaultTimeInSeconds,
  onChange,
  isDisabled = false,
}) => {
  const [relativeTime, setRelativeTime] = useState({
    ...getRelativeTimeFromSeconds(defaultTimeInSeconds),
  })

  const handleOnChange = useCallback(
    (e, { name, value }) => {
      e.preventDefault()
      const newRelativeTime = { ...relativeTime, [name]: value }
      setRelativeTime(newRelativeTime)
      onChange(getTimeFromRelativeObject(newRelativeTime))
    },
    [relativeTime, onChange]
  )

  return (
    <div>
      <Form.Field
        control={Input}
        placeholder='Time'
        type='number'
        disabled={isDisabled}
        required
        name='time'
        id='time'
        value={relativeTime.time}
        onChange={handleOnChange}
      />
      <Form.Field
        control={Select}
        options={RELATIVE_TIME_RANGE_TYPES}
        id='range-type'
        name='rangeType'
        value={relativeTime.rangeType}
        disabled={isDisabled}
        onChange={handleOnChange}
      />
    </div>
  )
}

export default RelativeRange
