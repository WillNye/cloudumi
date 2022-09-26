/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { TableTopBar } from '../../../../utils'
import { Segment } from 'semantic-ui-react'
import { roleAccessAuthColumns } from '../../columns'
import { EnablingRoleAccessAuth } from './EnablingRoleAccessAuth'
import { NewTag } from '../../forms/NewTag'
import { Bar, Fill } from 'lib/Misc'

export const RoleAccessAuth = ({ setAccessData, accessData }) => {
  const { get, post, remove } = useApi(
    'services/aws/role-access/credential-brokering/auth-tags',
    { shouldPersist: true }
  )

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add Tag')

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) get.do()
  }, [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({}, `${rowValues?.tag_name}`)
        .then(() => {
          success('Tag removed')
          get.do()
        })
        .catch(({ errorsMap, message }) => {
          error(errorsMap || message)
        })
    }
  }

  const handleFinish = () => {
    success('Tag created successfully!')
    get.do()
  }

  const handleClose = post.reset

  const columns = roleAccessAuthColumns({
    disabled: !accessData?.role_access,
    handleClick,
  })

  const label = `Status: ${get.status}${
    get.error ? ` / Error: ${get.error}` : ''
  }`

  const data = get.data

  const hasData = data?.length > 0

  const isWorking = get.status === 'working'

  const handleRefresh = () => get.do()

  return (
    <>
      <EnablingRoleAccessAuth
        setAccessData={setAccessData}
        accessData={accessData}
      />

      <Segment basic vertical disabled={!accessData?.role_access}>
        <DatatableWrapper
          isLoading={remove.status === 'working'}
          renderAction={
            <TableTopBar
              onClick={hasData ? openModal : null}
              extras={
                <Bar>
                  <Fill />
                  {get.timestamp.current() && (
                    <small>
                      <em>Last update: {get.timestamp.current()} </em>
                      &nbsp;&nbsp;&nbsp;
                    </small>
                  )}
                  <RefreshButton disabled={isWorking} onClick={handleRefresh} />
                </Bar>
              }
            />
          }
        >
          <Datatable
            data={data}
            columns={columns}
            emptyState={{
              label: 'Create Tag Name',
              onClick: openModal,
            }}
            isLoading={isWorking}
            loadingState={{ label }}
          />
        </DatatableWrapper>

        <ModalComponent onClose={handleClose} hideConfirm>
          <NewTag closeModal={closeModal} onFinish={handleFinish} />
        </ModalComponent>
      </Segment>
    </>
  )
}
