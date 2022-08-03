import { DateTime } from 'luxon'

export const formatISODate = (date) => {
  const jsdate = new Date(date)
  const dateObj = DateTime.fromJSDate(jsdate)
  return dateObj.toUTC().toFormat('dd MMM yyyy, hh:mm a')
}

const compareDates = (startDate, endDate) =>
  new Date(startDate).getTime() > new Date(endDate).getTime()

const updateDiffChanges = (newChange, oldChange) => {
  if (compareDates(newChange.updated_at, oldChange.updated_at)) {
    return {
      newVersion: newChange,
      oldVersion: oldChange,
    }
  } else {
    return {
      newVersion: oldChange,
      oldVersion: newChange,
    }
  }
}

export const getNewDiffChanges = (diffChanges, newChange) => {
  const { oldVersion, newVersion } = diffChanges
  if (
    !oldVersion ||
    compareDates(newVersion.updated_at, oldVersion.updated_at)
  ) {
    return updateDiffChanges(newVersion, newChange)
  } else {
    return updateDiffChanges(oldVersion, newChange)
  }
}
