import { createContext, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthProviderDefault'

const initialState = {
  data: null,
  status: 'waiting', // waiting/working/done
  error: null,
  empty: true,
}

export const url = 'api/v3';

const useInnerUtils = () => {

  const [state, setState] = useState({
    ...initialState,
  })

  const buildPath = (pathname = '') => url + (pathname ? '/' : '') + pathname

  const handleWorking = () => {
    setState({ data: null, status: 'working', error: null })
  }

  const handleResponse = (res) => {
    if (!res) {
      setState({ data: null, status: 'done', error: 'Error!' })
      return 'Error!'
    }

    const response = res?.data;

    setState({ data: response, status: 'done' })
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

const useGet = (commonPathname) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const get = async (pathname) => {
    handleWorking()
    const res = await sendRequestCommon(
      null,
      buildPath(`${commonPathname}${pathname ? '/' + pathname : ''}`),
      'get'
    )
    return handleResponse(res)
  }

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: get,
  }
}

const usePost = (commonPathname) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const post = async (body, pathname) => {
    handleWorking()
    const res = await sendRequestCommon(
      body || {},
      buildPath(`${commonPathname}${pathname ? '/' + pathname : ''}`),
      'post'
    )
    return handleResponse(res)
  }

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: post,
  }
}

const useRemove = (commonPathname) => {
  const { sendRequestCommon } = useAuth()

  const { state, buildPath, handleWorking, handleResponse, reset } =
    useInnerUtils()

  const remove = async (body, pathname) => {
    handleWorking()
    const res = await sendRequestCommon(
      body || {},
      buildPath(`${commonPathname}${pathname ? '/' + pathname : ''}`),
      'delete'
    )
    return handleResponse(res)
  }

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: remove,
  }
}

export const useApi = (commonPathname) => {
  return {
    get: useGet(commonPathname),
    post: usePost(commonPathname),
    remove: useRemove(commonPathname),
  }
}

export const ApiContext = createContext();

export const ApiGetProvider = ({
  children,
  pathname
}) => {

  const { get } = useApi(pathname);

  useEffect(() => get.do(), []);  

  return (
    <ApiContext.Provider value={{ data: get?.data }}>
      {children}
    </ApiContext.Provider>
  );
};
