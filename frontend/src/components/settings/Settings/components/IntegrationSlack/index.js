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
  const { register, watch } = useForm()

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

  const fields = watch()

  const onSubmit = (data) => {
    post
      .do({
        webhook_url: fields.webhook_url,
        enabled: fields.webhook_url ? true : false,
      })
      .then(() => {
        success(`Slack Webhook URL configuration is up to date`)
      })
      .catch(({ message }) => {
        error(message)
      })
  }

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

        <Form onSubmit={onSubmit}>
          <Form.Field>
            <label>Webhook URL</label>
            <input
              defaultValue={defaultValue}
              {...register('webhook_url', { required: true })}
            />
          </Form.Field>

          <Bar>
            <Fill />
            <Button type='submit' positive>
              Save
            </Button>
          </Bar>
        </Form>
      </Segment>
    </Section>
  )
}
