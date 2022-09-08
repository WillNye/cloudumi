import React, { useState } from 'react'
import { useApi } from 'hooks/useApi'
import { useForm } from 'react-hook-form'
import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'
import TypeaheadBlockComponent from 'components/blocks/TypeaheadBlockComponent'

const GROUPS_TITLE =
  'Groups this user is already a member of (added groups will also be shown in the list below)'

export const NewUser = ({ closeModal, onFinish, defaultValues }) => {
  const { register, handleSubmit, setValue, watch } = useForm({ defaultValues })

  const { post } = useApi('auth/cognito/users')

  const { get } = useApi('auth/cognito/groups')

  const [errorMessage, setErrorMessage] = useState(
    'Something went wrong, try again!'
  )

  const onSubmit = (data) => {
    post
      .do(data)
      .then(() => {
        closeModal()
        onFinish()
      })
      .catch(({ errorsMap, message }) => {
        setErrorMessage(errorsMap || message)
      })
  }

  const fields = watch()

  const isReady = fields.Username

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasError = post?.error && post?.status === 'done'

  const handleInputUpdate = (values) => {
    setValue('Groups', values, { required: true })
  }

  return (
    <Segment basic>
      <DimmerWithStates
        loading={isWorking}
        showMessage={hasError}
        messageType={isSuccess ? 'success' : 'warning'}
        message={errorMessage}
      />

      <Form onSubmit={handleSubmit(onSubmit)}>
        <Form.Field>
          <label>Username (Email)</label>
          <input {...register('Username', { required: true })} />
        </Form.Field>

        <TypeaheadBlockComponent
          handleInputUpdate={handleInputUpdate}
          required
          noQuery
          typeahead={`/api/v3/auth/cognito/groups`}
          label='Groups'
          defaultValues={fields?.Groups}
          defaultTitle={GROUPS_TITLE}
          sendRequestCommon={get.do}
          shouldTransformResults
          resultsFormatter={(results) =>
            results.map((item) => ({
              title: item.GroupName,
            }))
          }
        />

        {!defaultValues && (
          <p>
            <strong>
              A temporary password will be generated automatically and e-mailed
              to the user.
            </strong>
          </p>
        )}

        <Bar>
          <Fill />
          <Button type='submit' disabled={!isReady} positive>
            Submit
          </Button>
        </Bar>
      </Form>
    </Segment>
  )
}
