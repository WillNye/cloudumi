import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import {
  Button,
  Form,
  Segment,
  Label,
  Icon,
  Input,
  Dimmer,
  Loader,
} from 'semantic-ui-react'
import { Fill, Bar } from 'lib/Misc'
import { removeUserAccount } from './utils'

const UserGroups = ({ labels, setValue }) => (
  <div className='user-groups'>
    {labels.map((selectedValue, index) => {
      return (
        <Label basic color={'red'} key={index} size='mini'>
          {selectedValue}
          <Icon
            name='delete'
            onClick={() => {
              const newValues = removeUserAccount(labels, selectedValue)
              setValue('supported_groups', newValues)
            }}
          />
        </Label>
      )
    })}
  </div>
)

export const TempEscalationUserModal = ({
  elevated_access_config,
  updateUserGroups,
  isPolicyEditorLoading,
}) => {
  const [groupName, setGroupName] = useState('')
  const { handleSubmit, watch, setValue } = useForm({
    defaultValues: elevated_access_config,
  })

  const fields = watch()

  return (
    <Segment basic>
      <Dimmer active={isPolicyEditorLoading} inverted>
        <Loader />
      </Dimmer>
      <Form onSubmit={handleSubmit(updateUserGroups)}>
        <Form.Field>
          <label>Add Group Name</label>
          <Input
            placeholder='Add user groups ...'
            labelPosition='right'
            value={groupName}
            onChange={(e) => {
              e.preventDefault()
              setGroupName(e.target.value)
            }}
            label={
              <Button
                type='button'
                onClick={(e) => {
                  e.preventDefault()
                  if (!groupName) return
                  setValue('supported_groups', [
                    ...(fields.supported_groups || []),
                    groupName,
                  ])
                  setGroupName('')
                }}
              >
                Add
              </Button>
            }
          />
        </Form.Field>

        <UserGroups labels={fields.supported_groups} setValue={setValue} />
        <Bar>
          <Fill />
          <Button type='submit' disabled={isPolicyEditorLoading} positive>
            Submit
          </Button>
        </Bar>
      </Form>
    </Segment>
  )
}
