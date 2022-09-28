export const parseDate = (expDate) => {
  if (expDate) {
    return new Date(expDate)
  }
  return null
}

export const convertToISOFormat = (value) => new Date(value).toISOString()
