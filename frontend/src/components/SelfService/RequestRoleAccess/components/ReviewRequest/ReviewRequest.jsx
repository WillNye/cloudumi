import React from 'react'
import { Divider, Form, Header, Label } from 'semantic-ui-react'
import './ReviewRequest.scss'

const ReviewRequest = () => {
  return (
    <div className='review-request'>
      <Divider horizontal />
      <Header as='h4'>Review request</Header>
      <Divider horizontal />

      <div>
        <div className='review-request__row'>
          <div className='review-request__item'>Acccount</div>
          <div className='review-request__item'>Account Name</div>
        </div>
        <div className='review-request__row'>
          <div className='review-request__item'>Role</div>
          <div className='review-request__item'>Role Name</div>
        </div>
        <div className='review-request__row'>
          <div className='review-request__item'>Request access scope</div>
          <div className='review-request__item'>
            I want to request access for other users or groups
          </div>
        </div>
        <div className='review-request__row'>
          <div className='review-request__item'>User or Groups</div>
          <div className='review-request__item'>
            <Label.Group>
              <Label>Fun</Label>
              <Label>
                Happy
                <Label.Detail>22</Label.Detail>
              </Label>
              <Label>Smart</Label>
              <Label>Insane</Label>
              <Label>Exciting</Label>
            </Label.Group>
          </div>
        </div>
        <div className='review-request__row'>
          <div className='review-request__item'>Role</div>
          <div className='review-request__item'>Access Expiration</div>
        </div>
      </div>

      <Divider horizontal />

      <Form>
        <Form.Field>
          <label>Justification</label>
          <input placeholder='First Name' />
        </Form.Field>
      </Form>
    </div>
  )
}

export default ReviewRequest
