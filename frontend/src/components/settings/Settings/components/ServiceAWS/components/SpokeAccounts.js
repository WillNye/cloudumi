/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { NewSpokeAccount } from './forms/NewSpokeAccount'
import { str } from 'components/settings/Settings/strings'

import { spokeAccountsColumns } from './columns'
import { TableTopBar } from '../../utils'

export const SpokeAccounts = () => {
  const { get, post, remove } = useApi('services/aws/account/spoke')

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } =
    useModal('Add Spoke Account')

  useEffect(() => get.do(), [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({ name: rowValues?.name, account_id: rowValues?.account_id })
        .then(() => {
          success('Spoke Account removed')
          get.do()
        })
        .catch(() => error(str.toastErrorMsg))
    }
  }

  const handleClose = post.reset

  const columns = spokeAccountsColumns({ handleClick })

  const label = `Status: ${get.status}${
    get.error ? ` / Error: ${get.error}` : ''
  }`

  const data = get?.data

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
            label: 'Connect a Spoke Account',
            onClick: openModal,
          }}
          isLoading={isWorking}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={handleClose} hideConfirm>
        <NewSpokeAccount closeModal={closeModal} />
      </ModalComponent>
    </>
  )
}
