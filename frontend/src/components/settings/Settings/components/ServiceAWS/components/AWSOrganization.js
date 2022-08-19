/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { awsOrganizationColumns } from './columns'
import { NewOrganization } from './forms/NewOrganization'
import { TableTopBar } from '../../utils'
import { Bar, Fill } from 'lib/Misc'

export const AWSOrganization = () => {
  const [defaultValues, setDefaultValues] = useState({})

  const { get, post, remove } = useApi('services/aws/account/org', {
    shouldPersist: true,
  })

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add Organization')

  useEffect(() => {
    if (get.timestamp.compare().minutes >= 1 || get.empty) get.do()
  }, [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({ uuid: rowValues?.uuid })
        .then(() => {
          success('Organization removed')
          get.do()
        })
        .catch(({ errorsMap, message }) => {
          error(errorsMap || message)
        })
    }
    if (action === 'edit') {
      const newDefaultValues = {
        ...rowValues,
        account_name: `${rowValues.account_name} - ${rowValues.account_id}`,
      }
      setDefaultValues(newDefaultValues)
      openModal()
    }
  }

  const handleFinish = () => {
    success('Organization created successfully!')
    get.do()
  }

  const handleClose = () => {
    setDefaultValues({})
    post.reset()
  }

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
            label: 'Connect an AWS Organization',
            onClick: openModal,
          }}
          isLoading={isWorking}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={handleClose} hideConfirm>
        <NewOrganization
          closeModal={closeModal}
          onFinish={handleFinish}
          defaultValues={defaultValues}
        />
      </ModalComponent>
    </>
  )
}
