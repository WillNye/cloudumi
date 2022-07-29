import React, { useCallback, useState } from 'react'
import {
  Button,
  Comment,
  Divider,
  Header,
  Icon,
  Input,
  Message,
  Segment,
} from 'semantic-ui-react'

const CommentsFeedBlockComponent = (props) => {
  const { comments, requestID, reloadDataFromBackend } = props

  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [commentText, setCommentText] = useState('')

  const handleSubmitComment = useCallback(async () => {
    setIsLoading(true)
    setMessages([])
    const request = {
      modification_model: {
        command: 'add_comment',
        comment_text: commentText,
      },
    }
    const response = await props.sendRequestCommon(
      request,
      '/api/v2/requests/' + requestID,
      'PUT'
    )

    if (!response) {
      return
    }

    if (response.status === 403 || response.status === 400) {
      setIsLoading(false)
      setMessages([response.message])
      return
    }
    reloadDataFromBackend()
    setIsLoading(false)
    setCommentText('')
    setMessages([])
  }, [requestID, commentText]) // eslint-disable-line react-hooks/exhaustive-deps

  const messagesToShow =
    messages != null && messages.length > 0 ? (
      <Message negative>
        <Message.Header>An error occurred</Message.Header>
        <Message.List>
          {messages.map((message, index) => (
            <Message.Item key={index}>{message}</Message.Item>
          ))}
        </Message.List>
      </Message>
    ) : null

  const commentsContent =
    comments && comments.length > 0 ? (
      <Comment.Group>
        {comments.map((comment, index) => (
          <Comment key={index}>
            {comment.user && comment.user.photo_url ? (
              <Comment.Avatar src={comment.user.photo_url} />
            ) : (
              <Comment.Avatar src={<Icon name='user' size='big' />} />
            )}
            <Comment.Content>
              {comment.user && comment.user.details_url ? (
                <Comment.Author as='a'>
                  <a
                    href={comment.user.details_url}
                    target='_blank'
                    rel='noreferrer'
                  >
                    {comment.user_email}
                  </a>
                </Comment.Author>
              ) : (
                <Comment.Author as='text'>{comment.user_email}</Comment.Author>
              )}
              <Comment.Metadata>
                <div>{new Date(comment.timestamp).toLocaleString()}</div>
              </Comment.Metadata>
              <Comment.Text>{comment.text}</Comment.Text>
              <Comment.Actions>
                <Comment.Action>
                  <Divider />
                </Comment.Action>
              </Comment.Actions>
            </Comment.Content>
          </Comment>
        ))}
      </Comment.Group>
    ) : null

  const addCommentButton = (
    <Button
      content='Add comment'
      primary
      disabled={commentText === ''}
      onClick={handleSubmitComment}
    />
  )

  const commentInput = (
    <Input
      action={addCommentButton}
      placeholder='Add a new comment...'
      fluid
      icon='comment'
      iconPosition='left'
      onChange={(e) => setCommentText(e.target.value)}
      loading={isLoading}
      value={commentText}
    />
  )

  return (
    <Segment>
      <Header size='medium'>
        Comments <Icon name='comments' />
      </Header>
      {commentsContent}
      {messagesToShow}
      {commentInput}
    </Segment>
  )
}

export default CommentsFeedBlockComponent
