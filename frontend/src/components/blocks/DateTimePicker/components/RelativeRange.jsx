import React from 'react'
import { List } from 'semantic-ui-react'

const RelativeRange = () => {
  return (
    <List divided relaxed>
      <List.Item>
        <List.Content>
          <List.Description as='p'>Last 24 hours</List.Description>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Content>
          <List.Description as='p'>Last 7 days</List.Description>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Content>
          <List.Description as='p'>Last 30 days</List.Description>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Content>
          <List.Description as='p'>Last 3 months</List.Description>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Content>
          <List.Description as='p'>Last 6 months</List.Description>
        </List.Content>
      </List.Item>
      <List.Item>
        <List.Content>
          <List.Description as='p'>Last 12 months</List.Description>
        </List.Content>
      </List.Item>
    </List>
  )
}

export default RelativeRange
