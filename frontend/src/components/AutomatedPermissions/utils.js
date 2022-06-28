export const removePolicyRequest = async (
  sendRequestCommon,
  acountId,
  policyId
) =>
  sendRequestCommon(
    null,
    `/api/v3/automatic_policy_request_handler/aws/${acountId}/${policyId}`,
    'delete'
  )

export const approvePolicyRequest = async (
  sendRequestCommon,
  acountId,
  policyId
) =>
  sendRequestCommon(
    { permissions_flow: 'approve' },
    `/api/v3/automatic_policy_request_handler/aws/${acountId}/${policyId}`,
    'post'
  )

export const getAllPolicyRequests = async (sendRequestCommon) =>
  sendRequestCommon(null, '/api/v3/automatic_policy_request_handler/aws', 'get')

export const updatePolicyRequest = async (
  sendRequestCommon,
  acountId,
  policyId,
  data
) =>
  sendRequestCommon(
    data,
    `/api/v3/automatic_policy_request_handler/aws/${acountId}/${policyId}`,
    'put'
  )
