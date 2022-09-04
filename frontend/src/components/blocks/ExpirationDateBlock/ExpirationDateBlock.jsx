import React, { useCallback, useEffect, useState } from 'react'
import { Button, Header, Icon, Message, Segment, Form } from 'semantic-ui-react'
import DateTimePicker from '../DateTimePicker'
import { parseDate } from './utils'
import './ExpirationDateBlock.scss'

const ExpirationDateBlock = ({
  reloadDataFromBackend,
  requestID,
  expiration_date,
  sendRequestCommon,
  requestReadOnly,
  hasReadOnlyAccountPolicy,
}) => {
  const [expirationDate, setExpirationDate] = useState(
    parseDate(expiration_date)
  )
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessages, setErrorMessages] = useState([])

  useEffect(
    function onDateUpdate() {
      setExpirationDate(parseDate(expiration_date))
    },
    [expiration_date]
  )

  const handleSetPolicyExpiration = (value) => {
    if (!value) {
      setExpirationDate(null)
      return
    }
    setExpirationDate(value)
  }

  const handleSubmitComment = useCallback(async () => {
    setIsLoading(true)
    const request = {
      modification_model: {
        command: 'update_expiration_date',
        expiration_date: expirationDate
          ? new Date(expirationDate).toISOString()
          : expirationDate,
      },
    }

    const response = await sendRequestCommon(
      request,
      '/api/v2/requests/' + requestID,
      'PUT'
    )

    if (!response) {
      return
    }

    if (response.status === 403 || response.status === 400) {
      // Error occurred making the request
      setIsLoading(false)
      setErrorMessages([response.message])
      return
    }

    reloadDataFromBackend()
    setIsLoading(false)
    setErrorMessages([])
  }, [expirationDate, reloadDataFromBackend, requestID, sendRequestCommon])

  const messagesToShow =
    errorMessages.length > 0 ? (
      <Message negative>
        <Message.Header>An error occurred</Message.Header>
        <Message.List>
          {errorMessages.map((message, index) => (
            <Message.Item key={index}>{message}</Message.Item>
          ))}
        </Message.List>
      </Message>
    ) : null

  const updateDateButton = (
    <Button
      type='submit'
      content='Update Expiration Date'
      primary
      disabled={
        expirationDate === expiration_date ||
        isLoading ||
        hasReadOnlyAccountPolicy
      }
      onClick={handleSubmitComment}
      fluid
    />
  )

  const dateInput = (
    <Form>
      <Form.Field>
        <DateTimePicker
          onChange={handleSetPolicyExpiration}
          isDisabled={isLoading || requestReadOnly || hasReadOnlyAccountPolicy}
          defaultDate={expirationDate}
        />
      </Form.Field>

      {updateDateButton}
    </Form>
  )

  return (
    <Segment>
      <Header size='medium'>
        Expiration Date <Icon name='calendar times outline' />
      </Header>
      <Header as='h1'>
        <Header.Subheader>
          Set or update the expiration date for the requested permissions. If no
          date is set, the permissions will not expire.
        </Header.Subheader>
      </Header>
      {messagesToShow}

      <div className='expiration-date'>{dateInput}</div>
    </Segment>
  )
}

export default ExpirationDateBlock
