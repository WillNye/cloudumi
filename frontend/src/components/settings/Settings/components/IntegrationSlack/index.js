/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { SectionTitle } from '../utils'
import { Button, Form, Segment } from 'semantic-ui-react'
import { Section } from 'lib/Section'
import { useForm } from 'react-hook-form'
import { useApi } from 'hooks/useApi'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'
import { useToast } from 'lib/Toast'

export const IntegrationSlack = () => {
  const { register, handleSubmit, watch } = useForm()

  const { get, post } = useApi('slack')

  const [defaultValue, setDefaultValues] = useState('')

  const { error, success } = useToast()

  useEffect(
    () =>
      get.do().then((data) => {
        setDefaultValues(data?.webhook_url)
      }),
    []
  )

  const onSubmit = (data) => {
    post
      .do(data)
      .then(() => {
        success(`Slack Webhook URL configured`)
      })
      .catch(() => {
        error(`Error when trying to configure Slack Webhook URL`)
      })
  }

  const fields = watch()

  const isReady = fields.webhook_url !== ''

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasError = post?.error && post?.status === 'done'

  return (
    <Section title={<SectionTitle title='Slack' helpHandler='slack' />}>
      <Segment basic vertical>
        <DimmerWithStates
          loading={isWorking}
          showMessage={hasError}
          messageType={isSuccess ? 'success' : 'warning'}
          message={'Something went wrong, try again!'}
        />

        <Form onSubmit={handleSubmit(onSubmit)}>
          <Form.Field>
            <label>Webhook URL</label>
            <input
              defaultValue={defaultValue}
              {...register('webhook_url', { required: true })}
            />
          </Form.Field>

          <Bar>
            <Fill />
            <Button type='submit' disabled={!isReady} positive>
              Save
            </Button>
          </Bar>
        </Form>
      </Segment>
    </Section>
  )
}
