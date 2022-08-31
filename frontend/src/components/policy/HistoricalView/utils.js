import { DateTime } from 'luxon'

export const formatISODate = (stringDate) => {
  const dateObj = DateTime.fromSQL(stringDate, { zone: 'utc' })
  return dateObj.toFormat('dd MMM yyyy, hh:mm a')
}

const covertToJsDate = (stringDate) => {
  const dateObj = DateTime.fromSQL(stringDate, { zone: 'utc' })
  return dateObj.toJSDate()
}

const compareDates = (startDate, endDate) => {
  return covertToJsDate(startDate).getTime() > covertToJsDate(endDate).getTime()
}

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

export const getPreviousAssociatedPolicy = (resourceHistory, newVersion) => {
  const newVersionDateTime = covertToJsDate(newVersion.updated_at).getTime()
  const previousVersion = resourceHistory.find((version) => {
    const dateTime = covertToJsDate(version.updated_at).getTime()
    return (
      version.config_change.arn === newVersion.config_change.arn &&
      newVersionDateTime > dateTime
    )
  })
  return previousVersion ?? null
}
