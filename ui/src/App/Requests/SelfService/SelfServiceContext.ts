import React, { Dispatch } from 'react';
import { SELF_SERVICE_STEPS } from './constants';
import { ChangeTypeDetails, IRequest, RequestType, Identity } from './types';

export interface ISelfServiceContext {
  actions: {
    setCurrentStep: Dispatch<SELF_SERVICE_STEPS>;
    setSelectedProvider: Dispatch<string>;
    setSelectedIdentityType: Dispatch<string>;
    setSelectedIdentity: Dispatch<Identity>;
    setRequestTypes: Dispatch<RequestType[]>;
    setSelectedRequestType: Dispatch<RequestType>;
    setJustification: Dispatch<string>;
    setExpirationType: Dispatch<string>;
    setRelativeValue: Dispatch<string>;
    setRelativeUnit: Dispatch<string>;
    setDateValue: Dispatch<string>;
    setTimeValue: Dispatch<string>;
    addChange: (change: ChangeTypeDetails) => void;
    removeChange: (index: number) => void;
  };
  store: {
    currentStep: SELF_SERVICE_STEPS;
    selfServiceRequest: IRequest;
    expirationType: string;
    relativeValue: string;
    relativeUnit: string;
    dateValue: string;
    timeValue: string;
  };
}

const SelfServiceContext = React.createContext<ISelfServiceContext>(
  {} as ISelfServiceContext
);

export default SelfServiceContext;
