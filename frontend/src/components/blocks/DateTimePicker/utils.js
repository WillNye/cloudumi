import { DateTime } from 'luxon'

export const convertTime12to24 = (strTime) => {
  const [time, modifier] = strTime.split(' ')

  let [hours, minutes] = time.split(':')

  if (hours === '12') {
    hours = '00'
  }

  if (modifier === 'PM') {
    hours = parseInt(hours, 10) + 12
  }

  return `${hours}:${minutes}`
}

export const parseDate = (expDate) => {
  let date = null
  if (expDate) {
    date = DateTime.fromFormat(`${expDate}`, 'yyyyMMdd').toJSDate()
  }
  return date
}
