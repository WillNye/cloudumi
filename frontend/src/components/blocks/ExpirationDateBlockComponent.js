import React, { useCallback, useState } from 'react'
import { DateTime } from 'luxon'
import { Button, Header, Icon, Message, Segment, Form } from 'semantic-ui-react'
import SemanticDatepicker from 'react-semantic-ui-datepickers'

const ExpirationDateBlockComponent = ({
  reloadDataFromBackend,
  requestID,
  expiration_date,
  sendRequestCommon,
  requestReadOnly,
  hasReadOnlyAccountPolicy,
}) => {
  const [expirationDate, setExpirationDate] = useState(expiration_date)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessages, setErrorMessages] = useState([])

  const parseDate = (expDate) => {
    let date = null
    if (expDate) {
      date = DateTime.fromFormat(`${expDate}`, 'yyyyMMdd').toJSDate()
    }
    return date
  }

  const handleSetPolicyExpiration = (event, data) => {
    const currentDate = new Date()
    if (!data?.value) {
      setExpirationDate(null)
      return
    }

    if (currentDate.getTime() >= data.value.getTime()) {
      setExpirationDate(expiration_date)
      return
    }

    const dateObj = DateTime.fromJSDate(data.value)
    const dateString = dateObj.toFormat('yyyyMMdd')
    setExpirationDate(parseInt(dateString))
  }

  const handleSubmitComment = useCallback(async () => {
    setIsLoading(true)
    const request = {
      modification_model: {
        command: 'update_expiration_date',
        expiration_date: expirationDate,
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
      disabled={expirationDate === expiration_date || isLoading}
      onClick={handleSubmitComment}
    />
  )

  const dateInput = (
    <Form>
      <Form.Field>
        <Header as='h1'>
          <Header.Subheader>
            Set or update the expiration date for the requested permissions. If
            no date is set, the permissions will not expire.
          </Header.Subheader>
        </Header>
        <SemanticDatepicker
          filterDate={(date) => {
            const now = new Date()
            return date >= now
          }}
          disabled={isLoading || requestReadOnly}
          onChange={handleSetPolicyExpiration}
          type='basic'
          value={parseDate(expirationDate)}
          compact
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
      {messagesToShow}
      {dateInput}
    </Segment>
  )
}

export default ExpirationDateBlockComponent
