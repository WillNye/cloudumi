/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { str } from 'components/settings/Settings/strings'

import { groupColumns } from './columns'
import { TableTopBar } from '../../utils'
import NewGroup from '../forms/NewGroup'

export const Groups = () => {
  const { get, post, remove } = useApi('services/aws/account/spoke')

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add Group')

  // useEffect(() => get.do(), [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({}, `${rowValues?.name}/${rowValues?.account_id}`)
        .then(() => {
          success('Group REMOVED')
          get.do()
        })
        .catch(() => error(str.toastErrorMsg))
    }
  }

  const handleClose = post.reset

  const columns = groupColumns({ handleClick })

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
            label: 'Add Group',
            onClick: openModal,
          }}
          isLoading={isWorking}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={handleClose} hideConfirm>
        <NewGroup closeModal={closeModal} />
      </ModalComponent>
    </>
  )
}
