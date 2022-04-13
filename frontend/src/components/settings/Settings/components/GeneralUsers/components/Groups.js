/* eslint-disable react-hooks/exhaustive-deps */
import React, { useState, useEffect } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { str } from 'components/settings/Settings/strings'

import { groupColumns } from './columns'
import { TableTopBar } from '../../utils'
import { NewGroup } from '../forms/NewGroup'

export const Groups = () => {
  const { get, post, remove } = useApi('auth/cognito/groups', {
    shouldPersist: true,
  })

  const [defaultValues, setDefaultValues] = useState()

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add Group')

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) get.do()
  }, [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({ GroupName: rowValues?.GroupName })
        .then(() => {
          success('Group removed')
          get.do()
        })
        .catch(() => error(str.toastErrorMsg))
    }
    if (action === 'edit') {
      delete rowValues.RoleArn
      setDefaultValues(rowValues)
      openModal()
    }
  }

  const handleFinish = () => {
    success('Group created successfully!')
    get.do()
  }

  const handleClose = () => {
    setDefaultValues(null)
    post.reset()
  }

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
        <NewGroup
          closeModal={closeModal}
          onFinish={handleFinish}
          defaultValues={defaultValues}
        />
      </ModalComponent>
    </>
  )
}
