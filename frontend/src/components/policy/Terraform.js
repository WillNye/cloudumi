import React, { useState } from 'react'
import { Message, Header } from 'semantic-ui-react'
import { ReadOnlyPolicyMonacoEditor } from './PolicyMonacoEditor'

const Terraform = ({ terraform }) => {
  const [error, setError] = useState(null)
  const [messages, setMessages] = useState([])

  const onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(true)
      setMessages(JSON.stringify(lintErrors))
    } else {
      setError(false)
      setMessages([])
    }
  }

  // TODO: Make it possible to request a change that removes all unused permissions
  // TODO: Give the user commands to do this manually
  return (
    <div>
      <Header as='h2'>
        Terraform Export
        <Header.Subheader>
          This page provides a terraform export of the resource.
        </Header.Subheader>
      </Header>
      <ReadOnlyPolicyMonacoEditor
        onLintError={onLintError}
        policy={terraform}
        json={false}
        defaultLanguage={'hcl2'}
      />
      {error ? (
        <Message negative>
          <p>{messages}</p>
        </Message>
      ) : null}
    </div>
  )
}

export default Terraform
