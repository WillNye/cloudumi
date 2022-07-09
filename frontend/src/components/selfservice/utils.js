export const checkContainsReadOnlyAccount = (changes) => {
  const readOnlyChanges = changes.filter((change) => change.read_only)
  return Boolean(readOnlyChanges.length)
}
