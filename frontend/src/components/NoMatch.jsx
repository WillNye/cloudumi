import { Button, Divider, Header, Segment } from 'semantic-ui-react'
import { Link } from 'react-router-dom'

const NoMatch = () => {
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
          fontSize: '74px',
        }}
        textAlign='center'
      >
        404
        <Header.Subheader>Page not found!</Header.Subheader>
      </Header>
      <Divider horizontal />
      <Divider horizontal />
      <Link to='/'>
        <Button content='Return to Home' primary size='large' />
      </Link>
    </Segment>
  )
}

export default NoMatch
