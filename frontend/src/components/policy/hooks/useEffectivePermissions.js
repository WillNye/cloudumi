import { useEffect, useReducer } from 'react'
import { initialState, reducer } from './effectivePermissionsReducer'
import { usePolicyContext } from './PolicyProvider'

const useEffectivePermissions = () => {
  const [state, dispatch] = useReducer(reducer, initialState)
  const {
    resourceEffectivePermissions = {},
    setModalWithAdminAutoApprove,
    sendRequestV2,
  } = usePolicyContext()

  const handleEffectivePolicySubmit = async ({
    arn,
    justification,
    detachManagedPolicies,
  }) => {
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

            policy: {
              policy_document:
                resourceEffectivePermissions.data
                  ?.effective_policy_unused_permissions_removed,
            },
          },
        ],
      },
    })
  }

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
  }
}

export default useEffectivePermissions
