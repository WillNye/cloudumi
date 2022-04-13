/* eslint-disable react-hooks/exhaustive-deps */
import React, { useContext, useEffect, useState } from 'react'
import { ApiContext, useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { hubAccountColumns } from './columns'
import { NewHubAccount } from './forms/NewHubAccount'
import { TableTopBar } from '../../utils'
import { Bar, Fill } from 'lib/Misc'

export const HubAccount = () => {
  const { get, post, remove } = useApi('services/aws/account/hub', {
    shouldPersist: true,
  })

  const [defaultValues, setDefaultValues] = useState()

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal()

  const aws = useContext(ApiContext)

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) get.do()
  }, [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({ account_id: rowValues?.account_id })
        .then(() => {
          success('Hub Account removed')
          get.do()
        })
        .catch(({ errorsMap, message }) => {
          error(errorsMap || message)
        })
    }
    if (action === 'edit') {
      setDefaultValues(rowValues)
      openModal()
    }
  }

  const handleFinish = () => {
    success('Hub Account edited successfully!')
    get.do()
  }

  const handleClose = () => {
    setDefaultValues(null)
    post.reset()
  }

  const columns = hubAccountColumns({ handleClick })

  const label = `Status: ${get.status}${
    get.error ? ` / Error: ${get.error}` : ''
  }`

  let data = get.data

  const isDataReady = get.status === 'done' && !get.empty

  if (isDataReady || get.persisted) {
    data = data ? [data] : null
  } else {
    data = null
  }

  const isWorking = get.status === 'working'

  const handleRefresh = () => {
    get.do().then(() => aws.get())
  }

  return (
    <>
      <DatatableWrapper
        isLoading={remove.status === 'working'}
        renderAction={
          <TableTopBar
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
            label: 'Connect Hub Account',
            onClick: openModal,
          }}
          isLoading={isWorking}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent
        onClose={handleClose}
        hideConfirm
        forceTitle={defaultValues ? 'Edit Hub Account' : 'Add Hub Account'}
      >
        <NewHubAccount
          closeModal={closeModal}
          onFinish={handleFinish}
          defaultValues={defaultValues}
        />
      </ModalComponent>
    </>
  )
}
