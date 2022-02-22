import React, { createContext } from 'react'
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const ToastContext = createContext();

export const ToastProvider = ({ children }) => {
  return (
    <ToastContext.Provider value={{}}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
};

export const useToast = () => {  

  const defaultOptions = {
    onOpen: () => {},
    onClose: () => {},
    autoClose: 6000,
    type: 'default',
    hideProgressBar: false,
    position: 'top-right',
    pauseOnHover: false
  };
  
  const customToast = (message, options) => {
    
    const {
      onOpen = () => {},
      onClose = () => {},
      type, // info/success/warning/error/default
    } = options || {};
    
    toast(message, {
      ...defaultOptions,
      onOpen,
      onClose,
      type
    });
  };

  return {
    toast: customToast,
    success: (message, options) => customToast(message, { ...options, type: 'success' }),
    error: (message, options) => customToast(message, { ...options, type: 'error' }),
    dismiss: toast.dismiss
  };
};