/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect } from 'react'
import { useApi } from './useApi'

export const useGeoIP = () => {
  const { get } = useApi('reflection/ip')

  useEffect(() => get.do(), [])

  return {
    ...get,
  }
}
