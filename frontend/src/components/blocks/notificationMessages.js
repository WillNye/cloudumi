import React from 'react'
import { Grid, Header, Message, Segment } from 'semantic-ui-react'

export const ReadOnlyNotification = ({ isReadonlyInfo }) =>
  isReadonlyInfo ? (
    <Grid.Column>
      <Message info>
        <Message.Header>View only</Message.Header>
        <p>This change is view only and can not be modified.</p>
      </Message>
    </Grid.Column>
  ) : (
    <></>
  )

export const ErrorNotification = ({ messages }) =>
  messages.length > 0 ? (
    <Message negative>
      <Message.Header>There was a problem with your request</Message.Header>
      <Message.List>
        {messages.map((message) => (
          <Message.Item>{message}</Message.Item>
        ))}
      </Message.List>
    </Message>
  ) : (
    <></>
  )

export const ResponseNotification = ({ response }) =>
  response.length > 0 ? (
    <Grid.Column>
      {response.map((message, index) =>
        message.status === 'error' ? (
          <Message negative key={index}>
            <Message.Header>An error occurred</Message.Header>
            <Message.Content>{message.message}</Message.Content>
          </Message>
        ) : (
          <Message positive key={index}>
            <Message.Header>Success</Message.Header>-
            <Message.Content>{message.message}</Message.Content>
          </Message>
        )
      )}
    </Grid.Column>
  ) : (
    <></>
  )

export const AppliedNotification = ({ isApplied }) =>
  isApplied ? (
    <Grid.Column>
      <Message positive>
        <Message.Header>Change already applied</Message.Header>
        <p>This change has already been applied and cannot be modified.</p>
      </Message>
    </Grid.Column>
  ) : (
    <></>
  )

export const CancelledNotification = ({ isCancelled }) =>
  isCancelled ? (
    <Grid.Column>
      <Message negative>
        <Message.Header>Change cancelled</Message.Header>
        <p>This change has been cancelled and cannot be modified.</p>
      </Message>
    </Grid.Column>
  ) : (
    <></>
  )

export const ExpiredNotification = ({ isExpired }) =>
  isExpired ? (
    <Grid.Column>
      <Message negative>
        <Message.Header>Change expired</Message.Header>
        <p>This change has expired and cannot be modified.</p>
      </Message>
    </Grid.Column>
  ) : (
    <></>
  )

export const NullPolicyNotification = ({ isNullPolicy }) =>
  isNullPolicy ? (
    <Segment basic>
      <Header as='h1'>Null Policy</Header>
      <p>This change will remove all permissions from this role.</p>
    </Segment>
  ) : (
    <></>
  )
