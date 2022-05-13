export const removeUserAccount = (group, userAccount) => {
  return group.filter((user) => user !== userAccount)
}
