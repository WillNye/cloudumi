import React, { useState } from 'react'
import { Form } from 'semantic-ui-react'

const DropDownBlockComponent = (props) => {
  const { handleInputUpdate, defaultValue, options, required } = props

  const [actions, setActions] = useState(defaultValue || [])

  const handleActionChange = (_e, { value }) => {
    setActions(value)
    handleInputUpdate(value)
  }

  return (
    <Form.Field required={required || false}>
      <label>Select Desired Permissions</label>
      <Form.Dropdown
        multiple
        onChange={handleActionChange}
        options={options}
        placeholder=''
        selection
        value={actions}
      />
    </Form.Field>
  )
}

export default DropDownBlockComponent
