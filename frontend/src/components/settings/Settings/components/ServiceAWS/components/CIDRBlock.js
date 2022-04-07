/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { str } from 'components/settings/Settings/strings'
import { TableTopBar } from '../../utils'
import { Segment } from 'semantic-ui-react'
import { CIDRBlockColumns } from './columns'
import { NewCIDR } from './forms/NewCIDR'

export const CIDRBlock = () => {
  const { get, post, remove } = useApi('services/aws/ip-access')

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add CIDR')

  useEffect(() => get.do(), [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do({
          cidr: rowValues?.cidr,
        })
        .then(() => {
          success('CIDR removed')
          get.do()
        })
        .catch(({ errorsMap, message }) => {
          error(errorsMap || message)
        })
      }
  }

  const handleFinish = () => {
    success('CIDR added successfully!')
    get.do()
  }

  const handleClose = post.reset

  const columns = CIDRBlockColumns({ handleClick })

  const label = `Status: ${get.status}${
    get.error ? ` / Error: ${get.error}` : ''
  }`

  const data = get.data

  const hasData = data?.length > 0

  const isWorking = get.status === 'working'

  const handleRefresh = () => get.do()

  return (
    <Segment basic vertical>
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
            label: 'Add CIDR',
            onClick: openModal,
          }}
          isLoading={isWorking}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={handleClose} hideConfirm>
        <NewCIDR closeModal={closeModal} onFinish={handleFinish} />
      </ModalComponent>
    </Segment>
  )
}
