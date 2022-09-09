import { MINUTES } from './constants'

export const convertTime12to24 = (strTime) => {
  const [time, modifier] = strTime.split(' ')

  let [hours, minutes] = time.split(':')

  if (modifier === 'PM') {
    hours = parseInt(hours, 10) + 12
  }

  if (hours === 24) {
    hours = '00'
  }

  return { hours, minutes }
}

const autoCorrectTime = (currentMinutes) =>
  MINUTES.reduce((prev, curr) => {
    return Math.abs(curr.value - currentMinutes) <
      Math.abs(prev.value - currentMinutes)
      ? curr
      : prev
  })

export const getDefaultTime = (expDate) => {
  if (expDate) {
    const strTime = new Date(expDate).toLocaleTimeString('en-US', {
      // en-US can be set to 'default' to use user's browser settings
      hour: '2-digit',
      minute: '2-digit',
    })

    const [time, modifier] = strTime.split(' ')
    const [hours, minutes] = time.split(':')

    return {
      hours: parseInt(hours, 10),
      minutes: autoCorrectTime(parseInt(minutes, 10)).value,
      state: modifier,
    }
  }

  return null
}

export const setNewDateTime = (date, time) => {
  const jsDate = new Date(date)
  const { hours, minutes, state } = time
  const timeIn24 = convertTime12to24(`${hours}:${minutes} ${state}`)
  jsDate.setHours(timeIn24.hours, timeIn24.minutes)
  return jsDate
}
