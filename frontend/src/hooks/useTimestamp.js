export const useTimestamp = (commonKey) => {

  const storage = {
    get: (key) => {
      const saved = JSON.parse(sessionStorage.getItem('timestamp'))
      return typeof key === 'string' ? saved?.[key] : saved
    },
    set: (key, value) => {
      sessionStorage.setItem('timestamp', JSON.stringify({
        ...storage.get(),
        [key]: value
      }))
      return storage.get()
    },
    remove: (key) => sessionStorage.removeItem(key)
  }

  const generate = (key = commonKey) => {
    const dateNow = Date.now()
    if (typeof key === 'string') storage.set(key, dateNow)
    return dateNow
  }

  const remove = (key = commonKey) => {
    if (typeof key === 'string') storage.remove(key)
  }

  const reset = (key = commonKey) => {
    const dateNow = Date.now()
    if (typeof key === 'string') storage.set(key, dateNow)
    return dateNow
  }

  const current = (key = commonKey, convert) => {
    let saved = null
    if (typeof key === 'string') saved = storage.get(key)
    const date = new Date(saved);
    const output = date.toLocaleString()
    return saved && convert ? output : saved
  }

  const compare = (key = commonKey) => {
    const dateNow = Date.now()
    const saved = current(key)
    let diff = dateNow - saved
    const milliseconds = Math.round(diff / 1000) || 0;
    const minutes = new Date(diff).getMinutes() || 0;
    const hours = Math.round(minutes / 60) || 0;
    return {
      milliseconds,
      minutes,
      hours,
    }
  }

  return {
    init: generate,
    reset,
    remove,
    current,
    compare,
    commonKey
  }
}
