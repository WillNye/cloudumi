import React from 'react'
import Datatable from 'lib/Datatable'
import { DatatableWrapper } from 'lib/Datatable/ui/utils'
import { Section } from 'lib/Section'
import { ScreenHeading } from 'lib/Screen/styles'
import { SectionTitle } from '../utils'

import { userColumns } from '../GeneralUsers/components/columns'
import { TableTopBar } from '../utils'
import { useModal } from 'lib/hooks/useModal'

const data = [
  {
    user: 'curtis',
    enabled: true,
    email: 'curtis@foo.bar',
    updatedAt: '2021-04-04',
    createdAt: '2021-04-01',
    expiration: 'never',
  },
  {
    user: 'cspilhere',
    enabled: false,
    email: 'cspilhere@foo.bar',
    updatedAt: '2021-04-04',
    createdAt: '2021-04-01',
    expiration: 'never',
  },
]

export const IntegrationSSO = () => {
  const { openModal, ModalComponent } = useModal('New Provider')

  const handleClick = (action, rowValues) => {}

  const columns = userColumns({ handleClick })

  return (
    <>
      <ScreenHeading>Single Sign-On</ScreenHeading>

      <Section title={<SectionTitle title='SSO Providers' />}>
        <DatatableWrapper renderAction={<TableTopBar onClick={openModal} />}>
          <Datatable
            data={data}
            columns={columns}
            emptyState={{
              label: 'Add Provider',
              onClick: () => {},
            }}
          />
        </DatatableWrapper>

        <ModalComponent onClickToConfirm={() => {}}>Foo</ModalComponent>
      </Section>
    </>
  )
}
