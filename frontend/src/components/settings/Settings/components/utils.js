/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { Button, Input, Form } from 'semantic-ui-react'
import { Fill, Bar } from 'lib/Misc'
import { useApi } from 'hooks/useApi'
import { useHelpModal } from 'lib/hooks/useHelpModal'

export const SelectAccount = ({
  register,
  label,
  options = [],
  onOptionsLoad,
}) => {
  const { get } = useApi('services/aws/account/spoke')

  useEffect(() => {
    get.do().then(() => {
      onOptionsLoad && onOptionsLoad()
    })
    return () => {
      get.reset()
    }
  }, [])

  const handleOptions = (data) => {
    if (data)
      return data.map((i) => `${i.account_name || ''} - ${i.account_id}`)
    return options
  }

  const isLoading = get?.status === 'working'

  const isDone = get?.status === 'done'

  const isEmpty = isDone && get.empty

  return (
    <Form.Field>
      <label>{label}</label>
      <select {...register} disabled={isLoading || isEmpty}>
        {isEmpty && (
          <option value=''>
            You need at least one Spoke Account to proceed.
          </option>
        )}
        {!isLoading && <option value=''>Select provider type</option>}
        {!isLoading ? (
          handleOptions(get?.data).map((value, index) => (
            <option key={index} value={value}>
              {value}
            </option>
          ))
        ) : (
          <option value=''>Loading accounts...</option>
        )}
      </select>
    </Form.Field>
  )
}

export const SectionTitle = ({ title, helpHandler }) => {
  const { QuestionMark } = useHelpModal()

  return (
    <>
      <span>{title}</span>&nbsp;
      {helpHandler && <QuestionMark handler={helpHandler} />}
    </>
  )
}

export const TableTopBar = ({ onSearch, onClick, disabled, extras }) => {
  return (
    <Bar>
      {onSearch && (
        <Input
          size='small'
          label='Search'
          icon='search'
          disabled={disabled}
          onChange={onSearch}
        />
      )}
      <Fill />
      {extras}
      {onClick && (
        <Button
          compact
          color='blue'
          onClick={onClick}
          disabled={disabled}
          style={{ marginRight: 0 }}
        >
          New
        </Button>
      )}
    </Bar>
  )
}

export const SelectGroup = ({ register, label, options, defaultValues }) => {
  const { get } = useApi('auth/cognito/groups')

  useEffect(() => {
    if (!options) get.do()
    return () => {
      get.reset()
    }
  }, [])

  const handleOptions = (data) => {
    if (data) return data.map((i) => `${i.GroupName}`)
    return options || []
  }

  const isLoading = get?.status === 'working'

  const isDone = get?.status === 'done'

  const isEmpty = isDone && get.empty

  return (
    <Form.Field>
      <label>{label} (Cmd/Ctrl + Click to multi-select)</label>
      <select {...register} multiple disabled={isLoading || isEmpty}>
        {isEmpty && <option value=''>You dont have groups to select.</option>}
        {!isLoading ? (
          handleOptions(get?.data).map((value, index) => (
            <option
              key={index}
              value={value}
              selected={defaultValues.indexOf(value) !== -1}
            >
              {value}
            </option>
          ))
        ) : (
          <option value=''>Loading groups...</option>
        )}
      </select>
    </Form.Field>
  )
}

export const Password = ({ defaultValue }) => {
  const [isVisible, setVisibility] = useState(false)

  return (
    <Form.Field inline>
      <label>Password</label>
      <div>
        <Input
          type={isVisible ? 'text' : 'password'}
          defaultValue={defaultValue}
          disabled
        />
        &nbsp;
        <Button
          onClick={() => setVisibility(!isVisible)}
          icon={isVisible ? 'eye slash' : 'eye'}
          type='button'
        />
      </div>
    </Form.Field>
  )
}
