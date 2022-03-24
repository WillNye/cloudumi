/* eslint-disable react-hooks/exhaustive-deps */
import { createContext, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProviderDefault'

const initialState = {
  data: null,
  status: 'waiting', // waiting/working/done
  error: null,
  empty: true,
}

export const url = 'api/v3'

const useInnerUtils = () => {
  const [state, setState] = useState({
    ...initialState,
  })

  const buildPath = (pathname = '', customUrl) =>
    customUrl || url + (pathname ? '/' : '') + pathname

  const handleWorking = () => {
    setState({ data: null, status: 'working', error: null })
  }

  const handleResponse = (res) => {
    if (!res) {
      setState({ data: null, status: 'done', error: 'Error!' })
      return 'Error!'
    }
    if (res?.status_code === 400) {
      setState({ error: res?.message, status: 'done' })
      throw new Error(res?.message)
    }
    let response = res?.data
    setState({ data: response, status: 'done' })
    return response
  }

  const reset = () => {
    setState(initialState)
  }

  return {
    state,
    buildPath,
    handleWorking,
    handleResponse,
    reset,
  }
}

const useGet = (commonPathname, { url }) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const get = async (pathname) => {
    handleWorking()
    try {
      const res = await sendRequestCommon(
        null,
        buildPath(`${commonPathname}${pathname ? '/' + pathname : ''}`, url),
        'get'
      )
      return handleResponse(res)
    } catch (error) {
      throw new Error(error)
    }
  }

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: get,
  }
}

const usePost = (commonPathname, { url }) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const post = async (body, pathname) => {
    handleWorking()
    try {
      const res = await sendRequestCommon(
        body || {},
        buildPath(`${commonPathname}${pathname ? '/' + pathname : ''}`, url),
        'post'
      )
      return handleResponse(res)
    } catch (error) {
      throw new Error(error)
    }
  }

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: post,
  }
}

const useRemove = (commonPathname, { url }) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const remove = async (body, pathname) => {
    handleWorking()
    try {
      const res = await sendRequestCommon(
        body || {},
        buildPath(`${commonPathname}${pathname ? '/' + pathname : ''}`, url),
        'delete'
      )
      return handleResponse(res)
    } catch (error) {
      throw new Error(error)
    }
  }
  return {
    ...state,
    empty: !state?.data,
    reset,
    do: remove,
  }
}

export const useApi = (commonPathname, options = {}) => {
  return {
    get: useGet(commonPathname, options),
    post: usePost(commonPathname, options),
    remove: useRemove(commonPathname, options),
  }
}

export const ApiContext = createContext()

export const ApiGetProvider = ({ children, pathname }) => {
  const { get } = useApi(pathname)

  useEffect(() => get.do(), [])

  return (
    <ApiContext.Provider
      value={{
        status: get?.status,
        data: get?.data,
        error: get?.status,
        empty: get?.empty,
      }}
    >
      {children}
    </ApiContext.Provider>
  )
}
