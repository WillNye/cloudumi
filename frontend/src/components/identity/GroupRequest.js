import { DateTime } from 'luxon'
import React, { useCallback, useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useParams } from 'react-router-dom'
import SemanticDatepicker from 'react-semantic-ui-datepickers'
import {
  Button,
  Form,
  Header,
  Message,
  Table,
  TextArea,
} from 'semantic-ui-react'
import { useAuth } from '../../auth/AuthProviderDefault'

export const IdentityGroupRequest = (props) => {
  const auth = useAuth()
  const { sendRequestCommon } = auth
  const { idpName, groupName } = useParams()
  const [formContent, setFormContent] = useState('')
  const [group, setGroup] = useState(null)
  const [groupExpiration, setGroupExpiration] = useState(null)
  const [justification, setJustification] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [statusMessage, setStatusMessage] = useState(null)

  const [header, setHeader] = useState(null)

  const handleSubmit = useCallback(
    async (evt) => {
      const data = {
        justification: justification,
        groupExpiration: groupExpiration,
      }
      const resJson = await sendRequestCommon(
        data,
        '/api/v3/identities/requests/group/' + idpName + '/' + groupName
      )
      console.log(resJson)
      if (resJson.status !== 'success') {
        setErrorMessage(JSON.stringify(resJson))
      } else {
        setStatusMessage(
          <ReactMarkdown linkTarget='_blank' children={resJson.message} />
        )
      }
      // TODO: Post data and render response message/error in a generic way
    },
    [groupName, idpName, justification, groupExpiration, sendRequestCommon]
  )

  useEffect(() => {
    if (!group) {
      return
    }
    setFormContent(
      <Form>
        <Header as='h1'>
          <Header.Subheader>Justification</Header.Subheader>
        </Header>
        <TextArea
          placeholder='Reason for requesting access'
          onChange={(e) => {
            setJustification(e.target.value)
          }}
        />
        <Form.Field>
          <br />
          <Header as='h1'>
            <Header.Subheader>(Optional) Expiration</Header.Subheader>
          </Header>
          <SemanticDatepicker
            filterDate={(date) => {
              const now = new Date()
              return date >= now
            }}
            onChange={(e, data) => {
              if (!data?.value) {
                setGroupExpiration(null)
                return
              }
              const dateObj = DateTime.fromJSDate(data.value)
              const dateString = dateObj.toFormat('yyyyMMdd')
              setGroupExpiration(parseInt(dateString))
            }}
            type='basic'
            compact
          />
        </Form.Field>
        <br />

        <Button primary onClick={handleSubmit}>
          Submit Request
        </Button>
      </Form>
    )
  }, [group, handleSubmit])

  useEffect(() => {
    async function fetchDetails() {
      const resJson = await sendRequestCommon(
        null,
        '/api/v3/identities/group/' + idpName + '/' + groupName,
        'get'
      )
      if (!resJson) {
        return
      }

      if (!resJson?.group?.attributes?.requestable) {
        setHeader(
          <Header as='h2' color='red'>
            Group is not requestable
          </Header>
        )
        return
      }

      setGroup(resJson.group)

      // Set headers
      if (resJson?.headers) {
        setHeader(
          resJson.headers.map(function (header) {
            return (
              <Table.Row>
                <Table.Cell width={4}>{header.key}</Table.Cell>
                <Table.Cell>{header.value}</Table.Cell>
              </Table.Row>
            )
          })
        )
      }
    }
    fetchDetails()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <Header as='h3'>Group Request</Header>
      <Table celled striped definition>
        {header}
      </Table>
      {errorMessage ? (
        <Message negative>
          <p>{errorMessage}</p>
        </Message>
      ) : null}
      {statusMessage ? (
        <Message positive>
          <p>{statusMessage}</p>
        </Message>
      ) : null}
      {formContent}
    </div>
  )
}
