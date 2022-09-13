import React, { useCallback, useMemo } from 'react'
import Datatable from 'lib/Datatable'
import { useModal } from 'lib/hooks/useModal'
import { useApi } from 'hooks/useApi'
import { DatatableWrapper } from 'lib/Datatable/ui/utils'
import { TableTopBar } from '../../../settings/Settings/components/utils'
import { roleAccessColumns } from './columns'
import { usePolicyContext } from '../../hooks/PolicyProvider'
import { RoleAccessGroupModal } from './common'
import { Link } from 'react-router-dom'

const RoleAccess = ({ role_access_config }) => {
  const { openModal, closeModal, ModalComponent } = useModal(
    'Add User Groups for Role Access'
  )

  const {
    resource,
    setToggleRefreshRole,
    setIsPolicyEditorLoading,
    isPolicyEditorLoading,
  } = usePolicyContext()

  const { put } = useApi('/', {
    url: `/api/v2/roles/${resource.account_id}/${resource.name}/role-access-config`,
  })

  const authorized_groups = useMemo(() => {
    const groups = []
    role_access_config.noq_authorized_groups.forEach((tag) => {
      tag.value.forEach((group) => {
        groups.push({
          group_name: group,
          web_access: tag.web_access,
          tag_name: tag.tag_name,
        })
      })
    })
    return groups
  }, [role_access_config])

  const cli_authorized_groups = useMemo(() => {
    const groups = []
    role_access_config.noq_authorized_cli_groups.forEach((tag) => {
      tag.value.forEach((group) => {
        groups.push({
          group_name: group,
          web_access: tag.web_access,
          tag_name: tag.tag_name,
        })
      })
    })
    return groups
  }, [role_access_config])

  const updateUserGroups = (data) => {
    setIsPolicyEditorLoading(true)
    put
      .do(data)
      .then((response) => {
        setIsPolicyEditorLoading(false)
        closeModal()
        setToggleRefreshRole(true)
      })
      .catch(() => {
        setIsPolicyEditorLoading(false)
      })
  }

  const handleRemove = useCallback(
    (group) => {
      const data = { ...role_access_config }
      if (group.web_access) {
        data.noq_authorized_groups = data.noq_authorized_groups.map(
          (group_tag) => {
            if (group_tag.tag_name === group.tag_name) {
              group_tag.value = group_tag.value.filter(
                (value) => value !== group.group_name
              )
            }
            return group_tag
          }
        )
      } else {
        data.noq_authorized_cli_groups = data.noq_authorized_cli_groups.map(
          (group_tag) => {
            if (group_tag.tag_name === group.tag_name) {
              group_tag.value = group_tag.value.filter(
                (value) => value !== group.group_name
              )
            }
            return group_tag
          }
        )
      }
      updateUserGroups(data)
    },
    [role_access_config] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const columns = roleAccessColumns({ handleRemove })

  return (
    <>
      {role_access_config.is_valid_config ? (
        <>
          <p>
            Use the following IAM role tag values to identify users and groups
            authorized to retrieve role credentials.
          </p>
          <DatatableWrapper renderAction={<TableTopBar onClick={openModal} />}>
            <Datatable
              data={[...authorized_groups, ...cli_authorized_groups]}
              columns={columns}
              emptyState={{
                label: 'Add User Group',
                onClick: openModal,
              }}
              isLoading={false}
              loadingState={{ label: '' }}
            />
          </DatatableWrapper>

          <ModalComponent
            onClose={closeModal}
            hideConfirm
            forceTitle='Add Role Access User Groups'
          >
            <RoleAccessGroupModal
              role_access_config={role_access_config}
              updateUserGroups={updateUserGroups}
              isPolicyEditorLoading={isPolicyEditorLoading}
            />
          </ModalComponent>
        </>
      ) : (
        <div>
          Role Access Authorization is either not enabled or not properly
          configured. Visit&nbsp;<Link to='/settings'>settings</Link> page.
        </div>
      )}
    </>
  )
}

export default RoleAccess
