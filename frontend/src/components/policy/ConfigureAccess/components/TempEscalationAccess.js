import React, { useCallback, useMemo } from 'react'
import { useApi } from 'hooks/useApi'
import Datatable from 'lib/Datatable'
import { useModal } from 'lib/hooks/useModal'
import { DatatableWrapper } from 'lib/Datatable/ui/utils'
import { TableTopBar } from '../../../settings/Settings/components/utils'
import { TempEscalationUserModal } from './common'
import { usePolicyContext } from '../../hooks/PolicyProvider'
import { tempEscalationColumns } from './columns'
import { removeUserAccount } from './utils'
import { Link } from 'react-router-dom'

const TempEscalationAccess = ({ elevated_access_config }) => {
  const { openModal, closeModal, ModalComponent } = useModal(
    'Temporary Elevated Access Modal'
  )

  const {
    resource,
    setToggleRefreshRole,
    setIsPolicyEditorLoading,
    isPolicyEditorLoading,
  } = usePolicyContext()

  const { put } = useApi('/', {
    url: `/api/v2/roles/${resource.account_id}/${resource.name}/elevated-access-config`,
  })

  const data = useMemo(() => {
    return (elevated_access_config.supported_groups || []).map((group) => ({
      group_name: group,
    }))
  }, [elevated_access_config])

  const updateUserGroups = (data) => {
    setIsPolicyEditorLoading(true)
    put
      .do(data)
      .then(() => {
        setIsPolicyEditorLoading(false)
        closeModal()
        setToggleRefreshRole(true)
      })
      .catch(() => {
        setIsPolicyEditorLoading(false)
      })
  }

  const handleRemove = useCallback(
    async (group) => {
      const data = {
        ...elevated_access_config,
        supported_groups: removeUserAccount(
          elevated_access_config.supported_groups,
          group.group_name
        ),
      }
      await updateUserGroups(data)
    },
    [elevated_access_config] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const columns = tempEscalationColumns({
    handleRemove,
    disabled: !elevated_access_config.can_edit,
  })

  return (
    <>
      <p>
        Users who are members of the following groups will be able to request
        temporary access to this role. Approvals and notifications can be
        globally configured on the&nbsp;
        <Link to='/settings'>settings</Link> page.
      </p>
      <DatatableWrapper
        isLoading={false}
        renderAction={
          <TableTopBar
            onClick={data.length ? openModal : null}
            disabled={!elevated_access_config.can_edit}
          />
        }
      >
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Add User Group',
            onClick: openModal,
            disabled: !elevated_access_config.can_edit,
          }}
          loadingState={{ label: '' }}
        />
      </DatatableWrapper>
      <ModalComponent
        onClose={closeModal}
        hideConfirm
        forceTitle='Add Temporary Elevated Access User Groups'
      >
        <TempEscalationUserModal
          elevated_access_config={elevated_access_config}
          updateUserGroups={updateUserGroups}
          isPolicyEditorLoading={isPolicyEditorLoading}
        />
      </ModalComponent>
    </>
  )
}

export default TempEscalationAccess
