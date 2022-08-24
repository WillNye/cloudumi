import React from 'react'
import { useAuth } from 'auth/AuthProviderDefault'
import { Button, Divider, Header, Segment } from 'semantic-ui-react'
import { Link } from 'react-router-dom'

const ErrorBoundary = ({ children }) => {
  const { isInternalServerError, setIsInternalServerError } = useAuth()

  if (isInternalServerError) {
    return (
      <Segment
        basic
        style={{
          paddingTop: '120px',
          marginTop: '72px',
        }}
        textAlign='center'
      >
        <Header
          as='h1'
          color='grey'
          style={{
            fontSize: '24px',
          }}
          textAlign='center'
        >
          An Error Occurred
          <Divider horizontal />
          <Header.Subheader>
            Oops! We ran into an unexpected problem. Our team has been notified.
            Please try again later.
          </Header.Subheader>
        </Header>
        <Divider horizontal />
        <Link to='/' onClick={() => setIsInternalServerError(false)}>
          <Button content='Return to Home' primary size='large' />
        </Link>
      </Segment>
    )
  }

  return <>{children}</>
}

export default ErrorBoundary
