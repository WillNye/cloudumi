const { DateTime } = require('luxon')

export const parseDate = (expDate) => {
  let date = null
  if (expDate) {
    date = DateTime.fromFormat(`${expDate}`, 'yyyyMMdd').toJSDate()
  }
  return date
}
