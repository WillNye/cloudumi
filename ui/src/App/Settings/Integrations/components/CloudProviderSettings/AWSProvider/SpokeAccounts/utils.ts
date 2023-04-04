export const removeUserAccount = (group: string[], userAccount: string) => {
  return group.filter(user => user !== userAccount);
};
