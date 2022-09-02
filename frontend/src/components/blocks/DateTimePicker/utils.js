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
