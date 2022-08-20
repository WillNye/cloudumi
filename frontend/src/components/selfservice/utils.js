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
