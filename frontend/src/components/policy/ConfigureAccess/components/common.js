import React, { useCallback, useState } from 'react'
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
import { removeUserAccount, updateTagGroups } from './utils'

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
  const { watch, setValue } = useForm({
    defaultValues: elevated_access_config,
  })

  const fields = watch()

  return (
    <Segment basic>
      <Dimmer active={isPolicyEditorLoading} inverted>
        <Loader />
      </Dimmer>
      <Form>
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
                type='submit'
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
      </Form>

      <Bar>
        <Fill />
        <Button
          type='button'
          onClick={() => updateUserGroups({ ...fields })}
          disabled={isPolicyEditorLoading}
          positive
        >
          Submit
        </Button>
      </Bar>
    </Segment>
  )
}

export const RoleAccessGroupModal = ({
  role_access_config,
  updateUserGroups,
  isPolicyEditorLoading,
}) => {
  const { handleSubmit, watch, register } = useForm({
    defaultValues: { tag_name: '', web_access: false },
  })

  const fields = watch()

  const onSubmit = useCallback(
    async (data) => {
      const newRoleAccessdata = { ...role_access_config }

      if (data.web_access) {
        updateTagGroups(
          data,
          newRoleAccessdata.noq_authorized_groups || [],
          role_access_config.noq_authorized_tag
        )
      } else {
        updateTagGroups(
          data,
          newRoleAccessdata.noq_authorized_cli_groups || [],
          role_access_config.noq_authorized_cli_tag
        )
      }
      updateUserGroups(newRoleAccessdata)
    },
    [role_access_config] // eslint-disable-line react-hooks/exhaustive-deps
  )

  return (
    <Segment basic>
      <Dimmer active={isPolicyEditorLoading} inverted>
        <Loader />
      </Dimmer>
      <Form onSubmit={handleSubmit(onSubmit)}>
        <Form.Field>
          <label>Tag Name</label>
          <input {...register('tag_name', { required: true })} />
        </Form.Field>

        <Form.Field inline>
          <input id='check' type='checkbox' {...register('web_access')} />
          <label htmlFor='check'>Allow Web Console Access?</label>
        </Form.Field>

        <Bar>
          <Fill />
          <Button
            type='submit'
            disabled={isPolicyEditorLoading || !fields.tag_name}
            positive
          >
            Submit
          </Button>
        </Bar>
      </Form>
    </Segment>
  )
}
