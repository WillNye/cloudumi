import React, { useContext, useEffect, useReducer } from 'react'
import { useParams } from 'react-router-dom'
import { initialState, reducer } from './policyReducer'
import {
  getResourceEndpoint,
  getResourceEffectivePolicyEndpoint,
} from '../../../helpers/utils'
import { useAuth } from '../../../auth/AuthProviderDefault'

const PolicyContext = React.createContext(initialState)

export const usePolicyContext = () => useContext(PolicyContext)

export const PolicyProvider = ({ children }) => {
  const { sendRequestCommon, sendRequestV2 } = useAuth()
  const [state, dispatch] = useReducer(reducer, initialState)
  const { accountID, serviceType } = useParams()
  let { resourceName, region } = useParams()
  const allParams = useParams()
  if (allParams.hasOwnProperty('0') && serviceType === 'managed_policy') {
    // special case, managed policies can have a path, append to resourceName
    // wildcard will be added as key "0"
    resourceName = '/' + allParams['0'] + '/' + resourceName
  } else if (
    allParams.hasOwnProperty('0') &&
    (serviceType === 'sns' || serviceType === 'sqs')
  ) {
    // In the case of sns, sqs, the wildcard represents the region
    region = allParams['0']
  }
  // PolicyEditor States Handlers
  const setParams = (params) => dispatch({ type: 'UPDATE_PARAMS', params })
  const setResource = (resource) =>
    dispatch({ type: 'UPDATE_RESOURCE', resource })
  const setIsPolicyEditorLoading = (loading) =>
    dispatch({ type: 'TOGGLE_LOADING', loading })
  const setToggleDeleteRole = (toggle) =>
    dispatch({ type: 'TOGGLE_DELETE_ROLE', toggle })
  const setToggleRefreshRole = (toggle) =>
    dispatch({ type: 'TOGGLE_REFRESH_ROLE', toggle })
  const setIsSuccess = (isSuccess) =>
    dispatch({ type: 'SET_IS_SUCCESS', isSuccess })

  const setResourceEffectivePermissions = (resourceEffectivePermissions) =>
    dispatch({
      type: 'SET_RESOURCE_EFFECTIVE_PERMISSIONS',
      resourceEffectivePermissions,
    })

  // Resource fetching happens only when location is changed and when a policy is added/updated/removed.
  useEffect(() => {
    ;(async () => {
      // store resource metadata from the url
      setParams({ accountID, region, resourceName, serviceType })
      // get the endpoint by corresponding service type e.g. s3, iamrole, sqs
      const endpoint = getResourceEndpoint(
        accountID,
        serviceType,
        region,
        resourceName
      )
      // set loader to start fetching resource from the backend.
      setIsPolicyEditorLoading(true)
      // retrieve resource from the endpoint and set resource state
      const resource = await sendRequestCommon(null, endpoint, 'get')
      if (!resource) {
        return
      }
      setResource(resource)
      setIsPolicyEditorLoading(false)
    })()
  }, [accountID, region, resourceName, serviceType, state.isSuccess]) //eslint-disable-line

  // Effective Permissions fetching only happens when location is changed and when a policy is added/updated/removed.
  useEffect(() => {
    ;(async () => {
      // store resource metadata from the url
      setParams({ accountID, region, resourceName, serviceType })
      if (serviceType !== 'iamrole') {
        return
      }
      // get the endpoint by corresponding service type e.g. s3, iamrole, sqs
      const endpoint = getResourceEffectivePolicyEndpoint(
        accountID,
        serviceType,
        region,
        resourceName
      )
      // retrieve resource from the endpoint and set resource state
      const resourceEffecivePermissions = await sendRequestCommon(
        null,
        endpoint,
        'get'
      )
      if (!resourceEffecivePermissions) {
        return
      }
      setResourceEffectivePermissions(resourceEffecivePermissions)
    })()
  }, [accountID, region, resourceName, serviceType, state.isSuccess]) //eslint-disable-line

  useEffect(() => {
    ;(async () => {
      const endpoint = getResourceEndpoint(
        accountID,
        serviceType,
        region,
        resourceName
      )
      if (!state.toggleRefreshRole) {
        return
      }
      setIsPolicyEditorLoading(true)
      const resource = await sendRequestCommon(
        null,
        `${endpoint}?force_refresh=true`,
        'get'
      )
      if (!resource) {
        return
      }
      setResource(resource)
      setIsPolicyEditorLoading(false)
      setToggleRefreshRole(false)
    })()
  }, [state.toggleRefreshRole]) //eslint-disable-line

  // Mostly used for Justification Modal
  const setModalWithAdminAutoApprove = (approve) =>
    dispatch({ type: 'SET_ADMIN_AUTO_APPROVE', approve })
  const setTogglePolicyModal = (toggle) =>
    dispatch({ type: 'TOGGLE_POLICY_MODAL', toggle })
  const setShowExpirationDate = (visible) =>
    dispatch({ type: 'SHOW_SET_EXPIRATION_DATE', visible })

  const handleDeleteRole = async (justification) => {
    const { serviceType, accountID, resourceName } = state.params

    const resourceType = serviceType === 'iamrole' ? 'role' : 'user'
    const principalArn = state?.resource?.arn

    const payload = {
      changes: {
        changes: [
          {
            principal: {
              principal_type: 'AwsResource',
              principal_arn: principalArn,
              account_id: accountID,
              name: resourceName,
              resource_type: resourceType,
            },
            change_type: 'delete_resource',
          },
        ],
      },
      justification,
      dry_run: false,
      admin_auto_approve: false,
    }

    return await sendRequestCommon(payload, '/api/v2/request')
  }

  // There are chances that same state and handler exists in other hooks
  return (
    <PolicyContext.Provider
      value={{
        ...state,
        setResource,
        setIsPolicyEditorLoading,
        setToggleDeleteRole,
        setToggleRefreshRole,
        setIsSuccess,
        setTogglePolicyModal,
        setModalWithAdminAutoApprove,
        setShowExpirationDate,
        handleDeleteRole,
        sendRequestV2,
      }}
    >
      {children}
    </PolicyContext.Provider>
  )
}
