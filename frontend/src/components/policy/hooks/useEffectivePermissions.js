import { useEffect, useReducer } from 'react'
import { initialState, reducer } from './effectivePermissionsReducer'
import { usePolicyContext } from './PolicyProvider'

const useEffectivePermissions = () => {
  const [state, dispatch] = useReducer(reducer, initialState)
  const { resourceEffectivePermissions = {} } = usePolicyContext()

  useEffect(() => {
    dispatch({
      type: 'SET_RESOURCE_EFFECTIVE_PERMISSIONS',
      policies: resourceEffectivePermissions,
    })
  }, [resourceEffectivePermissions])

  return {
    ...state,
    resourceEffectivePermissions: resourceEffectivePermissions?.data,
  }
}

export default useEffectivePermissions
