import React, { Dispatch } from 'react';
import { SELF_SERICE_STEPS } from './constants';
import { ChangeType, ChangeTypeDetails, RequestType } from './types';
export interface ISelfServiceContext {
  actions: {
    setCurrentStep: Dispatch<SELF_SERICE_STEPS>;
    setSelectedProvider: Dispatch<string>;
    setSelectedRequestType: Dispatch<RequestType>;
    setSelectedChangeType: Dispatch<ChangeType>;
    addChange: (change: ChangeTypeDetails) => void;
    removeChange: (change: ChangeTypeDetails) => void;
  };
  store: {
    currentStep: SELF_SERICE_STEPS;
    selectedProvider: string;
    selectedRequestType: RequestType;
    selectedChangeType: ChangeType;
    requestedChanges: ChangeTypeDetails[];
  };
}

const SelfServiceContext = React.createContext<ISelfServiceContext>(
  {} as ISelfServiceContext
);

export default SelfServiceContext;
