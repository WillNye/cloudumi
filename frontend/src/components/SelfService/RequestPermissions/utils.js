export const checkContainsReadOnlyAccount = (changes) => {
  const readOnlyChanges = changes.filter((change) => change.read_only)
  return Boolean(readOnlyChanges.length)
}

export const containsCondensedPolicyChange = (changes) => {
  const effectivePermissionsChanges = changes.filter(
    (change) => change.change_type === 'policy_condenser'
  )
  return Boolean(effectivePermissionsChanges.length)
}

export const containsResourceCreation = (changes) => {
  const effectivePermissionsChanges = changes.filter(
    ({ change_type }) =>
      change_type === 'create_resource' || change_type === 'delete_resource'
  )
  return Boolean(effectivePermissionsChanges.length)
}
