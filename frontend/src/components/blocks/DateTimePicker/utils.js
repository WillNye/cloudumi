import { DateTime } from 'luxon'
import {
  DAY_TO_SECONDS,
  HOUR_TO_SECONDS,
  RELATIVE_TIME_RANGE_TYPES,
  WEEK_TO_SECONDS,
} from './constants'

export const convertTime12to24 = (strTime) => {
  const [time, modifier] = strTime.split(' ')

  const [hours, minutes] = time.split(':')

  let hoursIn24 = hours

  if (modifier === 'PM' || hours === '12') {
    hoursIn24 = parseInt(hours, 10) + 12
  }

  if (hoursIn24 === 24) {
    hoursIn24 = '00'
  }

  return { hours: hoursIn24, minutes }
}

export const getDefaultTime = (expDate) => {
  if (expDate) {
    const strTime = new Date(expDate).toLocaleTimeString('en-US', {
      hour12: true,
      hour: 'numeric',
      minute: 'numeric',
    })

    const [time, modifier] = strTime.split(' ')
    const [hours, minutes] = time.split(':')

    return {
      hours: parseInt(hours, 10),
      minutes: minutes,
      state: modifier,
    }
  }

  return null
}

export const setNewDateTime = (date, time) => {
  const jsDate = new Date(date)
  const { hours, minutes, state } = time
  const timeIn24 = convertTime12to24(`${hours}:${minutes} ${state}`)
  jsDate.setHours(timeIn24.hours)
  return jsDate
}

export const getRelativeTimeFromSeconds = (time) => {
  if (time >= WEEK_TO_SECONDS) {
    return {
      time: `${Math.floor(time / WEEK_TO_SECONDS)}`,
      rangeType: RELATIVE_TIME_RANGE_TYPES.find((x) => x.value === 'WEEKS')
        .value,
    }
  }

  if (time >= DAY_TO_SECONDS) {
    return {
      time: `${Math.floor(time / DAY_TO_SECONDS)}`,
      rangeType: RELATIVE_TIME_RANGE_TYPES.find((x) => x.value === 'DAYS')
        .value,
    }
  }

  return {
    time: `${Math.floor(time / HOUR_TO_SECONDS)}`,
    rangeType: RELATIVE_TIME_RANGE_TYPES.find((x) => x.value === 'HOURS').value,
  }
}

export const getTimeFromRelativeObject = (relativeTime) => {
  const { time, rangeType } = relativeTime

  if (rangeType === 'WEEKS') {
    return time * WEEK_TO_SECONDS
  }

  if (rangeType === 'DAYS') {
    return time * DAY_TO_SECONDS
  }

  return time * HOUR_TO_SECONDS
}

export const getUserTimeZone = () =>
  DateTime.fromJSDate(new Date()).toFormat('ZZZZ')
