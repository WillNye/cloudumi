import React, { useState } from 'react'
import { Form } from 'semantic-ui-react'

const TextInputBlockComponent = (props) => {
  const { defaultValue, required, label, handleInputUpdate } = props

  const [value, setValue] = useState(defaultValue || '')

  const handleTextInputChange = (e) => {
    const { value } = e.target
    setValue(value)
    handleInputUpdate(value)
  }

  return (
    <Form.Field required={required}>
      <label>{label || 'Enter Value'} test</label>
      <input
        onChange={handleTextInputChange}
        placeholder='Enter your value here'
        value={value}
        type='text'
      />
    </Form.Field>
  )
}

export default TextInputBlockComponent
