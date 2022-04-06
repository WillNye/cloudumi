/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils'
import { useModal } from 'lib/hooks/useModal'
import { useToast } from 'lib/Toast'
import { str } from 'components/settings/Settings/strings'
import { SectionTitle, TableTopBar } from '../utils'
import { Segment } from 'semantic-ui-react'
import { integrationSSOColumns } from './columns'
import { NewProvider } from './forms/NewProvider'
import { Section } from 'lib/Section'

export const IntegrationSSO = () => {
  const { get, post, remove } = useApi('auth/sso')

  const [defaultValues, setDefaultValues] = useState([])

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add Provider')

  useEffect(() => get.do(), [])

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove
        .do()
        .then(() => {
          success('Provider removed')
          get.do()
        })
        .catch(() => error(str.toastErrorMsg))
    }
    if (action === 'edit') {
      setDefaultValues(rowValues)
      openModal()
    }
  }

  const handleFinish = (response) => {
    if (response?.success) {
      success('Provider added successfully!')
      get.do()
    } else {
      error(response?.message)
    }
  }

  const handleClose = () => {
    setDefaultValues(null)
    post.reset()
  }

  const columns = integrationSSOColumns({ handleClick })

  const label = `Status: ${get.status}${
    get.error ? ` / Error: ${get.error}` : ''
  }`

  const data = get?.data

  const preparedData = []

  data?.google && preparedData.push(data?.google)
  data?.saml && preparedData.push(data?.saml)
  data?.oidc && preparedData.push(data?.oidc)

  const hasData = preparedData?.length > 0

  const isWorking = get.status === 'working'

  const handleRefresh = () => get.do()

  return (
    <Section title={<SectionTitle title='Single Sign-On' helpHandler='sso' />}>
      <Segment basic vertical>
        <DatatableWrapper
          isLoading={remove.status === 'working'}
          renderAction={
            <TableTopBar
              onClick={
                hasData ? (preparedData?.length !== 3 ? openModal : null) : null
              }
              extras={
                <RefreshButton disabled={isWorking} onClick={handleRefresh} />
              }
            />
          }
        >
          <Datatable
            data={preparedData}
            columns={columns}
            emptyState={{
              label: 'Add Provider',
              onClick: openModal,
            }}
            isLoading={isWorking}
            loadingState={{ label }}
          />
        </DatatableWrapper>

        <ModalComponent onClose={handleClose} hideConfirm>
          <NewProvider
            closeModal={closeModal}
            onFinish={handleFinish}
            defaultValues={defaultValues}
            current={preparedData}
            existentProviders={data}
          />
        </ModalComponent>
      </Segment>
    </Section>
  )
}
