import { useCallback, useEffect, useReducer, useState } from 'react'
import { initialState, reducer } from './effectivePermissionsReducer'
import { usePolicyContext } from './PolicyProvider'

const useEffectivePermissions = () => {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [newStatement, setNewStatement] = useState(null)
  const [removeUnusedPermissions, setRemoveUnusedPermissions] = useState(false)
  const {
    resourceEffectivePermissions = {},
    setModalWithAdminAutoApprove,
    sendRequestV2,
  } = usePolicyContext()

  const handleEffectivePolicySubmit = useCallback(
    async ({ arn, justification, detachManagedPolicies }) => {
      return sendRequestV2({
        justification,
        admin_auto_approve: false,
        dry_run: false,
        changes: {
          changes: [
            {
              principal: {
                principal_arn: arn,
                principal_type: 'AwsResource',
              },
              change_type: 'policy_condenser',
              detach_managed_policies: detachManagedPolicies,
              remove_unused_permissions: removeUnusedPermissions,
              policy: {
                policy_document: newStatement,
              },
            },
          ],
        },
      })
    },
    [newStatement, sendRequestV2, removeUnusedPermissions]
  )

  useEffect(() => {
    dispatch({
      type: 'SET_RESOURCE_EFFECTIVE_PERMISSIONS',
      policies: resourceEffectivePermissions,
    })
  }, [resourceEffectivePermissions])

  return {
    ...state,
    resourceEffectivePermissions: resourceEffectivePermissions?.data,
    handleEffectivePolicySubmit,
    setModalWithAdminAutoApprove,
    newStatement,
    setNewStatement,
    setRemoveUnusedPermissions,
  }
}

export default useEffectivePermissions
