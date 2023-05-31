import React, { Dispatch } from 'react';
import { SELF_SERICE_STEPS } from './constants';

export interface ISelfServiceContext {
  actions: {
    setCurrentStep: Dispatch<SELF_SERICE_STEPS>;
  };
  store: {
    currentStep: SELF_SERICE_STEPS;
  };
}

const SelfServiceContext = React.createContext<ISelfServiceContext>(
  {} as ISelfServiceContext
);

export default SelfServiceContext;
