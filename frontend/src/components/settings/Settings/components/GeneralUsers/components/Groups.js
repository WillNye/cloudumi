import React from 'react'
import Datatable from 'lib/Datatable'
import { DatatableWrapper } from 'lib/Datatable/ui/utils'

import { groupColumns } from './columns'
import { TableTopBar } from '../../utils'
import { useModal } from 'lib/hooks/useModal'

const data = [
  {
    name: 'admins',
    description: 'AWS Admins',
    updatedAt: '2021-04-04',
    createdAt: '2021-04-01',
  },
]

export const Groups = () => {
  const { openModal, ModalComponent } = useModal('New Group')

  const handleClick = (action, rowValues) => {}

  const columns = groupColumns({ handleClick })

  return (
    <>
      <DatatableWrapper renderAction={<TableTopBar onClick={openModal} />}>
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Create Group',
            onClick: () => {},
          }}
        />
      </DatatableWrapper>

      <ModalComponent onClickToConfirm={() => {}}>Foo</ModalComponent>
    </>
  )
}
