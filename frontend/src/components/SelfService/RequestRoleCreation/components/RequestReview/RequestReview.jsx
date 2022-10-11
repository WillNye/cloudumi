import { useAuth } from 'auth/AuthProviderDefault'
import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Button,
  Divider,
  Form,
  Message,
  Segment,
  Table,
} from 'semantic-ui-react'
import { ROLE_CREATION_STEPS } from '../../constants'

const RequestReview = ({ formData, setCurrentStep }) => {
  const [justification, setJustification] = useState('')
  const [successAlert, setSuccessAlert] = useState(null)
  const [errorAlert, setErrorAlert] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const { sendRequestCommon } = useAuth()

  const handleSubmit = useCallback(async () => {
    const payload = {
      changes: {
        changes: [
          {
            principal: {
              principal_type: 'AwsResource',
              account_id: formData.account.account_id,
              name: formData.roleName,
              resource_type: 'role',
            },
            change_type: 'create_resource',
            instance_profile: true,
            description: formData.description,
          },
        ],
      },
      justification,
      dry_run: false,
      admin_auto_approve: false,
    }

    setIsLoading(true)
    setErrorAlert(null)
    setSuccessAlert(null)

    const response = await sendRequestCommon(payload, '/api/v2/request')

    if (response) {
      const { request_created, request_id, request_url } = response
      if (request_created === true) {
        setSuccessAlert({
          requestId: request_id,
          requestUrl: request_url,
        })
      } else {
        setErrorAlert(
          'Server reported an error with the request: ' +
            JSON.stringify(response)
        )
      }
    } else {
      setErrorAlert('Failed to submit request')
    }

    setIsLoading(false)
  }, [formData, justification]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Segment basic loading={isLoading}>
      <Table basic>
        <Table.Body>
          <Table.Row>
            <Table.Cell>Account</Table.Cell>
            <Table.Cell>{formData?.account?.title}</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Role</Table.Cell>
            <Table.Cell>{formData.roleName}</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Description</Table.Cell>
            <Table.Cell>{formData.description}</Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>

      <Divider horizontal />

      <Form>
        <Form.TextArea
          required
          label='Justification'
          placeholder='Tell us why you need this change'
          onChange={(e) => setJustification(e.target.value)}
          defaultValue={justification}
        />

        <Divider horizontal />

        {successAlert && (
          <Message positive>
            <Message.Header>Click below to view request</Message.Header>
            <p>
              <b>
                <Link to={successAlert.requestUrl}>
                  {successAlert.requestId}
                </Link>
              </b>
            </p>
          </Message>
        )}

        {errorAlert && (
          <Message negative>
            <Message.Header>An Error Occured</Message.Header>
            <p>{errorAlert}</p>
          </Message>
        )}
        <Divider horizontal />
        <div className='role-creation__step-actions'>
          <Button
            primary
            type='button'
            onClick={() => setCurrentStep(ROLE_CREATION_STEPS.STEP_ONE)}
            disabled={!!successAlert}
          >
            Back
          </Button>
          <Button
            type='submit'
            primary
            onClick={handleSubmit}
            disabled={!(justification || '').trim() || !!successAlert}
          >
            Submit
          </Button>
        </div>
      </Form>
    </Segment>
  )
}

export default RequestReview
