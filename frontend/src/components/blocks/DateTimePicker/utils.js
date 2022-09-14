import { DateTime } from 'luxon'
import {
  DAY_TO_SECONDS,
  HOUR_TO_SECONDS,
  RELATIVE_TIME_RANGE_TYPES,
  WEEK_TO_SECONDS,
} from './constants'

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
