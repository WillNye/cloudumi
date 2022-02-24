import React from 'react'

import { Message, Dimmer, Loader } from 'semantic-ui-react'

export const DimmerWithStates = ({
  loading,
  showMessage,
  messageType,
  message,
}) => {
  const types = {
    error: messageType === 'error',
    info: messageType === 'info',
    success: messageType === 'success',
    warning: messageType === 'warning',
  }

  return (
    <>
      <Dimmer inverted active={loading}>
        {loading && <Loader inverted />}
      </Dimmer>

      <Dimmer inverted active={showMessage}>
        {showMessage && (
          <Message {...types}>
            <Message.Header>{message}</Message.Header>
          </Message>
        )}
      </Dimmer>
    </>
  )
}
