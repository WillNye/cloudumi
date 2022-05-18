import React from 'react'
import { useForm } from 'react-hook-form'
import { Button, Form, Segment, Checkbox, Header } from 'semantic-ui-react'
import Datatable from 'lib/Datatable'
import { useModal } from 'lib/hooks/useModal'
import { DatatableWrapper } from 'lib/Datatable/ui/utils'
import { Fill, Bar } from 'lib/Misc'
import { TableTopBar } from '../../../settings/Settings/components/utils'

const RoleAccess = ({ tags }) => {
  const { register, handleSubmit } = useForm()

  const { openModal, closeModal, ModalComponent } = useModal(
    'Add User Groups for Role Access'
  )

  return (
    <>
      <Header as='h2'>
        Role Access
        <Header.Subheader>
          Use the following IAM role tag values to identify users and groups
          authorized to retrieve role credentials.
        </Header.Subheader>
      </Header>

      <DatatableWrapper renderAction={<TableTopBar onClick={openModal} />}>
        <Datatable
          data={tags}
          columns={[
            {
              Header: 'Group',
              accessor: 'group_name',
            },
            {
              Header: 'Allow Web Access',
              accessor: 'web_access',
              align: 'center',
              Cell: ({ row }) => (
                <Checkbox
                  toggle
                  onChange={() => {}}
                  false
                  defaultChecked={true}
                />
              ),
            },
            {
              Header: 'Actions',
              width: 80,
              align: 'right',
              Cell: ({ row }) => (
                <Button size='mini' onClick={() => {}} disabled={true}>
                  Remove
                </Button>
              ),
            },
          ]}
          emptyState={{
            label: 'Add User Group',
            onClick: openModal,
          }}
          isLoading={false}
          loadingState={{ label: '' }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={closeModal} hideConfirm>
        <Segment basic>
          {/* <DimmerWithStates
        // loading={isWorking}
        // showMessage={hasError}
        // messageType={isSuccess ? 'success' : 'warning'}
        // message={errorMessage}
      /> */}

          <Form onSubmit={handleSubmit(() => {})}>
            <Form.Field>
              <label>Tag Name</label>
              <input {...register('tag_name', { required: true })} />
            </Form.Field>

            <Form.Field inline>
              <input
                id='check'
                type='checkbox'
                {...register('allow_webconsole_access')}
              />
              <label htmlFor='check'>Allow Web Console Access?</label>
            </Form.Field>

            <Bar>
              <Fill />
              <Button type='submit' disabled={true} positive>
                Submit
              </Button>
            </Bar>
          </Form>
        </Segment>
      </ModalComponent>
    </>
  )
}

export default RoleAccess
