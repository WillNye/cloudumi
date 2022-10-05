import { useAuth } from 'auth/AuthProviderDefault'
import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Button,
  Divider,
  Form,
  Header,
  Label,
  Message,
  Segment,
  TextArea,
} from 'semantic-ui-react'
import { ACCESS_SCOPE, STEPS } from '../../constants'
import './ReviewRequest.scss'

const ReviewRequest = ({
  role,
  accessScope,
  expirationDate,
  userGroups,
  setCurrentStep,
}) => {
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
            principal: role.principal,
            change_type: 'assume_role_access',
            action: 'add',
            identities: userGroups.map((group) => group.name),
          },
        ],
      },
      justification,
      dry_run: false,
      admin_auto_approve: false,
      expiration_date: expirationDate,
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
  }, [role, accessScope, expirationDate, userGroups, justification])

  return (
    <Segment loading={isLoading} basic>
      <div className='review-request'>
        <Divider horizontal />
        <Header as='h4'>Review request</Header>
        <Divider horizontal />

        <div>
          <div className='review-request__row'>
            <div className='review-request__item'>Acccount</div>
            <div className='review-request__item'>{role.account_name}</div>
          </div>
          <div className='review-request__row'>
            <div className='review-request__item'>Role</div>
            <div className='review-request__item'>{role.arn}</div>
          </div>
          <div className='review-request__row'>
            <div className='review-request__item'>Request access scope</div>
            <div className='review-request__item'>
              {accessScope === ACCESS_SCOPE.SELF
                ? 'I want to request access for my self'
                : 'I want to request access for other users or groups'}
            </div>
          </div>
          <div className='review-request__row'>
            <div className='review-request__item'>User Groups</div>
            <div className='review-request__item'>
              <Label.Group>
                {userGroups.map((group, index) => (
                  <Label key={index}>{group.name}</Label>
                ))}
              </Label.Group>
            </div>
          </div>
          <div className='review-request__row'>
            <div className='review-request__item'>Access expiration</div>
            <div className='review-request__item'>
              {new Date(expirationDate).toLocaleString()}
            </div>
          </div>
        </div>

        <Divider horizontal />

        <Form>
          <TextArea
            placeholder='Tell us why you need this change'
            onChange={(e) => setJustification(e.target.value)}
            style={{ width: 'fluid' }}
            defaultValue={justification}
          />
        </Form>
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
        <div className='step-actions'>
          <Button
            primary
            onClick={() => setCurrentStep(STEPS.STEP_TWO)}
            disabled={!!successAlert}
          >
            Back
          </Button>
          <Button
            primary
            onClick={handleSubmit}
            disabled={
              !userGroups.length ||
              !(justification || '').trim() ||
              !!successAlert
            }
          >
            Submit
          </Button>
        </div>
      </div>
    </Segment>
  )
}

export default ReviewRequest
