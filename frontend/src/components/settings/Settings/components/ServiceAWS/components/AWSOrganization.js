/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { awsOrganizationColumns } from './columns'
import { NewOrganization } from './forms/NewOrganization'
import { str } from 'components/settings/Settings/strings'
import { TableTopBar } from '../../utils'

export const AWSOrganization = () => {
  const { get, post, remove } = useApi('services/aws/account/org')

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add Organization')

  useEffect(() => get.do(), [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({}, `${rowValues?.account_name}`)
        .then(() => {
          success('Organization REMOVED')
          get.do()
        })
        .catch(() => error(str.toastErrorMsg))
    }
  }

  const handleFinish = () => {
    success('Organization created successfully!')
    get.do()
  }

  const handleClose = post.reset

  const columns = awsOrganizationColumns({ handleClick })

  const label = `Status: ${get.status}${
    get.error ? ` / Error: ${get.error}` : ''
  }`

  const data = get.data

  const hasData = data?.length > 0

  const isWorking = get.status === 'working'

  const handleRefresh = () => get.do()

  return (
    <>
      <DatatableWrapper
        isLoading={remove.status === 'working'}
        renderAction={
          <TableTopBar
            onClick={hasData ? openModal : null}
            extras={
              <RefreshButton disabled={isWorking} onClick={handleRefresh} />
            }
          />
        }
      >
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Connect an AWS Organization',
            onClick: openModal,
          }}
          isLoading={isWorking}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={handleClose} hideConfirm>
        <NewOrganization closeModal={closeModal} onFinish={handleFinish} />
      </ModalComponent>
    </>
  )
}
