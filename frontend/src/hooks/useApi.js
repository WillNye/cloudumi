/* eslint-disable react-hooks/exhaustive-deps */
import { createContext, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProviderDefault'
import { useTimestamp } from './useTimestamp'
import create from 'zustand'
import { persist } from 'zustand/middleware'

const initialState = {
  data: null,
  status: 'waiting', // waiting/working/done
  error: null,
  empty: true,
  persisted: false,
}

const usePersistence = create(
  persist(
    (set, get) => ({
      update: (key, data) =>
        set({
          ...get(),
          [key]: data,
        }),
      delete: (key) => {
        const store = { ...get() }
        delete store[key]
        set(store)
      },
      clear: () => set({}),
    }),
    {
      name: 'persistence',
      getStorage: () => sessionStorage,
    }
  )
)

export const url = 'api/v3'

const useInnerUtils = (persistedState) => {
  const [state, setState] = useState({
    ...initialState,
    data: persistedState?.data || null,
    empty: !persistedState?.data,
    persisted: !!persistedState?.data,
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
      throw res
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

const useGet = (commonPathname, options) => {
  const { sendRequestCommon } = useAuth()

  const persistedState = usePersistence?.getState()?.[commonPathname]

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils(persistedState)

  const {
    init,
    reset: resetTimestamp,
    remove,
    current,
    compare,
  } = useTimestamp(commonPathname)

  const get = async (pathname) => {
    handleWorking()
    try {
      const res = await sendRequestCommon(
        null,
        buildPath(
          `${commonPathname}${pathname ? '/' + pathname : ''}`,
          options?.url
        ),
        'get'
      )
      if (options?.shouldPersist) {
        usePersistence.setState({
          ...usePersistence.getState(),
          [commonPathname]: {
            data: res?.data,
            timestamp: init(),
          },
        })
      }
      return handleResponse(res)
    } catch (error) {
      throw new Error(error)
    }
  }

  return {
    ...state,
    empty: !state?.data,
    status: state?.data ? 'done' : state.status,
    reset,
    do: get,
    timestamp: {
      reset: () => resetTimestamp(),
      remove: () => remove(),
      current: () => current(undefined, true),
      compare: () => compare(),
    },
  }
}

const usePost = (commonPathname, options) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const post = async (body, pathname) => {
    handleWorking()
    try {
      const res = await sendRequestCommon(
        body || {},
        buildPath(
          `${commonPathname}${pathname ? '/' + pathname : ''}`,
          options?.url
        ),
        'post'
      )
      return handleResponse(res)
    } catch (error) {
      const errorsHandler = (errors) =>
        errors.map((err) => (
          <p style={{ margin: 0, textAlign: 'center' }}>
            <small>{err}</small>
          </p>
        ))
      const formattedError = {
        message: error?.message,
        errorsMap: error?.errors ? errorsHandler(error?.errors) : null,
        errorsJoin: error?.errors ? error?.errors.join(',') : null,
        errors: error?.errors,
      }
      throw formattedError
    }
  }

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: post,
  }
}

const useRemove = (commonPathname, options) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const remove = async (body, pathname) => {
    handleWorking()
    try {
      const res = await sendRequestCommon(
        body || {},
        buildPath(
          `${commonPathname}${pathname ? '/' + pathname : ''}`,
          options?.url
        ),
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

export const useApi = (commonPathname, options) => {
  return {
    get: useGet(commonPathname, options),
    post: usePost(commonPathname, options),
    remove: useRemove(commonPathname, options),
  }
}

export const ApiContext = createContext()

export const ApiGetProvider = ({ children, pathname }) => {
  const { get } = useApi(pathname)

  const { init, reset, remove, current, compare } = useTimestamp(pathname)

  useEffect(
    () =>
      get.do().then(() => {
        init()
        return () => {
          remove()
        }
      }),
    []
  )

  return (
    <ApiContext.Provider
      value={{
        get: get.do,
        status: get?.status,
        data: get?.data,
        error: get?.status,
        empty: get?.empty,
        timestamp: {
          reset: () => reset(),
          remove: () => remove(),
          current: () => current(undefined, true),
          compare: () => compare(),
        },
      }}
    >
      {children}
    </ApiContext.Provider>
  )
}
