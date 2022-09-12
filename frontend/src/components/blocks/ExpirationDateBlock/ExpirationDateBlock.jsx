import React, { useCallback, useEffect, useState } from 'react'
import { Button, Header, Icon, Message, Segment, Form } from 'semantic-ui-react'
import DateTimePicker from '../DateTimePicker'
import { convertToISOFormat, parseDate } from './utils'
import './ExpirationDateBlock.scss'
import { useMemo } from 'react'

const ExpirationDateBlock = ({
  reloadDataFromBackend,
  requestID,
  expiration_date,
  sendRequestCommon,
  requestReadOnly,
  hasReadOnlyAccountPolicy,
  ttl,
}) => {
  const [expirationDate, setExpirationDate] = useState(
    parseDate(expiration_date)
  )
  const [timeInSeconds, setTimeInSeconds] = useState(ttl)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessages, setErrorMessages] = useState([])

  const showTTLOnly = useMemo(() => {
    return ttl && !expiration_date
  }, [ttl, expiration_date])

  const shouldNotUpdate = useMemo(() => {
    return (
      ttl === timeInSeconds &&
      convertToISOFormat(expirationDate) === convertToISOFormat(expiration_date)
    )
  }, [ttl, expiration_date, timeInSeconds, expirationDate])

  useEffect(
    function onDateUpdate() {
      setExpirationDate(parseDate(expiration_date))
    },
    [expiration_date]
  )

  useEffect(
    function onTTLUpdate() {
      setTimeInSeconds(ttl)
    },
    [ttl]
  )

  const handleUpdateExpiration = useCallback(
    async (request) => {
      setIsLoading(true)

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
    },
    [reloadDataFromBackend, requestID, sendRequestCommon]
  )

  const handleSubmit = useCallback(async () => {
    if (showTTLOnly) {
      const request = {
        modification_model: {
          command: 'update_ttl',
          ttl: timeInSeconds,
        },
      }
      handleUpdateExpiration(request)
    } else {
      const request = {
        modification_model: {
          command: 'update_expiration_date',
          expiration_date: expirationDate
            ? convertToISOFormat(expirationDate)
            : expirationDate,
        },
      }
      handleUpdateExpiration(request)
    }
  }, [timeInSeconds, expirationDate, showTTLOnly, handleUpdateExpiration])

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
      content='Set New Time'
      primary
      disabled={shouldNotUpdate || isLoading || hasReadOnlyAccountPolicy}
      onClick={handleSubmit}
      fluid
    />
  )

  const dateInput = (
    <Form>
      <Form.Field>
        <DateTimePicker
          onDateSelectorChange={setExpirationDate}
          onRelativeTimeChange={setTimeInSeconds}
          isDisabled={isLoading || requestReadOnly || hasReadOnlyAccountPolicy}
          defaultDate={expirationDate}
          defaultTimeInSeconds={timeInSeconds}
          showDateSelector={!showTTLOnly}
          showRelativeRange={showTTLOnly}
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
          {showTTLOnly
            ? 'Choose a relative expiration time that will apply after the request is approved'
            : `Set or update the expiration date for the requested permissions. If no
                date is set, the permissions will not expire.`}
        </Header.Subheader>
      </Header>
      {messagesToShow}

      <div className='expiration-date'>{dateInput}</div>
    </Segment>
  )
}

export default ExpirationDateBlock
