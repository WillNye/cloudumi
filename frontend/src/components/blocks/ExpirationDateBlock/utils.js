export const parseDate = (expDate) => {
  if (expDate) {
    return new Date(expDate)
  }
  return null
}
