import { useState } from 'react';
import { useAuth } from '../auth/AuthProviderDefault';

const initialState = {
  data: null,
  status: 'waiting', // waiting/working/done
  error: null,
  empty: true
};

const useInnerUtils = () => {

  const [state, setState] = useState({
    ...initialState
  });

  const buildPath = (commonPathName, pathName) => commonPathName + (pathName ? '/' : '') + pathName;

  const handleWorking = () => {
    setState({ data: null, status: 'working', error: null });
  };

  const handleResponse = (res) => {
    if (!res) {
      setState({ data: null, status: 'done', error: 'Error!' });
      return 'Error!';
    }
    setState({ data: res?.data, status: 'done' });
  };

  const reset = () => {
    setState(initialState);
  };

  return {
    state,
    buildPath,
    handleWorking,
    handleResponse,
    reset
  };

};

const useGet = (commonPathName) => {

  const { sendRequestCommon } = useAuth();

  const {
    state,
    buildPath,
    handleWorking,
    handleResponse,
    reset
  } = useInnerUtils();

  const get = async (pathName) => {
    handleWorking();
    const res = await sendRequestCommon(null, buildPath(commonPathName, pathName), 'get');
    return handleResponse(res);
  };

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: get
  };

};

export const usePost = (commonPathName) => {

  const { sendRequestCommon } = useAuth();

  const {
    state,
    buildPath,
    handleWorking,
    handleResponse,
    reset
  } = useInnerUtils();

  const post = async (pathName, body) => {
    handleWorking();
    const res = await sendRequestCommon(body || {}, buildPath(commonPathName, pathName), 'post');
    return handleResponse(res);
  };

  return {
    ...state,
    empty: !state?.data,
    reset,
    do: post
  };

};

export const useApi = (commonPathName) => {
  return {
    get: { ...useGet(commonPathName) },
    post: { ...usePost(commonPathName) }
  };
};