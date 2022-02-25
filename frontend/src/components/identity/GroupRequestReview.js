import React, { useCallback, useEffect, useState } from 'react'
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
import ReactMarkdown from 'react-markdown'

// TODO: Need loading modal
// TODO: Message responses from backend should be closable
// TODO: User should be able to see advanced view of entire request

export const IdentityGroupRequestReview = (props) => {
  const auth = useAuth()
  const { sendRequestCommon } = auth
  const { requestId } = useParams()
  const [formContent, setFormContent] = useState('')
  const [groupRequest, setGroupRequest] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const [statusMessage, setStatusMessage] = useState(null)
  const [reviewComment, setReviewComment] = useState(null)
  const [tableContent, setTableContent] = useState(null)

  const handleSubmit = useCallback(
    async (evt, action) => {
      const data = {
        comment: reviewComment,
        action: action,
      }
      const resJson = await sendRequestCommon(
        data,
        '/api/v3/identities/group_requests/' + requestId
      )
      console.log(resJson)
      if (resJson?.status !== 'success') {
        setErrorMessage(JSON.stringify(resJson))
      } else {
        setStatusMessage(
          <ReactMarkdown linkTarget='_blank' children={resJson.message} />
        )
      }
      // TODO: Post data and render response message/error in a generic way
    },
    [requestId, reviewComment, sendRequestCommon]
  )

  // TODO: Support back-and-forth commenting like we have for policy requests
  //   const commentsContent = extendedRequest.comments ? (
  //     <CommentsFeedBlockComponent
  //       comments={extendedRequest.comments}
  //       reloadDataFromBackend={this.reloadDataFromBackend}
  //       requestID={requestID}
  //       sendRequestCommon={this.props.sendRequestCommon}
  //     />
  //   ) : null;

  // TODO: Allow overriding user expiration date

  useEffect(() => {
    async function fetchGroupRequestDetails() {
      const resJson = await sendRequestCommon(
        null,
        '/api/v3/identities/group_requests/' + requestId,
        'get'
      )
      if (!resJson) {
        return
      }
      setGroupRequest(resJson.data)
    }
    fetchGroupRequestDetails()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!groupRequest) {
      return
    }
    setTableContent(
      Object.keys(groupRequest.requests_table).map(function (key) {
        return (
          <Table.Row>
            <Table.Cell width={4}>{key}</Table.Cell>
            <Table.Cell>{groupRequest.requests_table[key]}</Table.Cell>
          </Table.Row>
        )
      })
    )

    setFormContent(
      <Form>
        <Header as='h1'>
          <Header.Subheader>Reviewer Comment</Header.Subheader>
        </Header>
        <TextArea
          placeholder='Reviewer Comment'
          onChange={(e) => {
            setReviewComment(e.target.value)
          }}
        />
        <Form.Field>
          <br />
          <Header as='h1'>
            <Header.Subheader>(Optional) Update Expiration</Header.Subheader>
          </Header>
          <SemanticDatepicker
            filterDate={(date) => {
              const now = new Date()
              return date >= now
            }}
            // onChange={(e, data) => {
            //     if (!data?.value) {
            //         setGroupExpiration(null);
            //         return;
            //     }
            //     const dateObj = DateTime.fromJSDate(data.value);
            //     const dateString = dateObj.toFormat("yyyyMMdd");
            //     setGroupExpiration(parseInt(dateString))
            // }
            // }
            type='basic'
            compact
          />
        </Form.Field>
        <br />

        <Button
          primary
          onClick={(evt) => {
            handleSubmit(evt, 'approved')
          }}
        >
          Approve
        </Button>
        <Button
          negative
          onClick={(evt) => {
            handleSubmit(evt, 'cancelled')
          }}
        >
          Cancel
        </Button>
        {/* TODO: Support Re-opening Request */}
        {/* <Button negative onClick={(evt) => {handleSubmit(evt, "re-open")}}>Re-Open Request</Button> */}
      </Form>
    )
  }, [groupRequest]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <Header as='h3'>Group Request Review</Header>
      <Table celled striped definition>
        {tableContent}
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
