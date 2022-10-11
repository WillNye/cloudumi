import React from 'react'
import { Link } from 'react-router-dom'
import { Divider, Header, Segment } from 'semantic-ui-react'

const SelfServiceWizard = () => {
  return (
    <Segment basic>
      <Header as='h3'>Self-Service Wizard</Header>
      <Header.Subheader as='p'>What would you like to do?</Header.Subheader>
      <Divider horizontal />

      <Segment>
        <Header as='h4'>Request Permissions</Header>
        <Link to='/selfservice/permissions'>Continue</Link>

        <Divider />

        <Header as='h4'>Create an IAM Role</Header>
        <Link to='/selfservice/role/create'>Continue</Link>

        <Divider />

        <Header as='h4'>Request Access to an IAM Role</Header>
        <Link to='/selfservice/role/access'>Continue</Link>
      </Segment>
      <Divider horizontal />
    </Segment>
  )
}

export default SelfServiceWizard
