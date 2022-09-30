import React from 'react'
import { Button, Divider, Form, Header, Search } from 'semantic-ui-react'
import { STEPS } from '../../constants'

const SelectUserGroups = ({ setCurrentStep }) => {
  return (
    <div>
      <Divider horizontal />
      <Header as='h4'>Choose users or groups</Header>
      <Divider horizontal />

      <Form widths='equal'>
        <Header as='h5'>Request Access Scope</Header>

        <Form.Field>
          <Form.Radio
            label='Choose this'
            name='radioGroup'
            value='this'
            // checked={this.state.value === 'this'}
            // onChange={this.handleChange}
          />
        </Form.Field>
        <Form.Field>
          <Form.Radio
            label='Or that'
            name='radioGroup'
            value='that'
            // checked={this.state.value === 'that'}
            // onChange={this.handleChange}
          />
        </Form.Field>

        <Header as='h5'>Groups for Access</Header>

        <Form.Field required>
          <Search
            fluid
            //   loading={isLoading}
            //   onResultSelect={this.handleResultSelect.bind(this)}
            //   onSearchChange={_.debounce(
            //     this.handleSearchChange.bind(this),
            //     500,
            //     {
            //       leading: true,
            //     }
            //   )}
            //   results={results}
            //   resultRenderer={this.resultRenderer}
            //   value={value}
            placeholder='Enter role here'
          />
        </Form.Field>
      </Form>

      <div className='step-actions'>
        <Button
          primary
          onClick={() => setCurrentStep(STEPS.STEP_ONE)}
          // disabled={!Boolean(principal)}
        >
          Back
        </Button>
        <Button
          primary
          onClick={() => setCurrentStep(STEPS.STEP_THREE)}
          // disabled={!Boolean(principal)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}

export default SelectUserGroups
