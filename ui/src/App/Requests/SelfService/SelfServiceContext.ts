import React, { Dispatch } from 'react';
import { SELF_SERICE_STEPS } from './constants';
import { ChangeTypeDetails, IRequest, RequestType } from './types';
export interface ISelfServiceContext {
  actions: {
    setCurrentStep: Dispatch<SELF_SERICE_STEPS>;
    setSelectedProvider: Dispatch<string>;
    setSelectedRequestType: Dispatch<RequestType>;
    addChange: (change: ChangeTypeDetails) => void;
    removeChange: (index: number) => void;
  };
  store: {
    currentStep: SELF_SERICE_STEPS;
    selfServiceRequest: IRequest;
  };
}

const SelfServiceContext = React.createContext<ISelfServiceContext>(
  {} as ISelfServiceContext
);

export default SelfServiceContext;
