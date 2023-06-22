import React, { Dispatch } from 'react';
import { EXPIRATION_TYPE, SELF_SERVICE_STEPS } from './constants';
import { ChangeTypeDetails, IRequest, RequestType, Identity } from './types';

export interface ISelfServiceContext {
  actions: {
    setCurrentStep: Dispatch<SELF_SERVICE_STEPS>;
    setSelectedProvider: Dispatch<string>;
    setSelectedIdentityType: Dispatch<string>;
    setSelectedIdentity: Dispatch<Identity>;
    setSelectedRequestType: Dispatch<RequestType>;
    setJustification: Dispatch<string>;
    setExpirationType: Dispatch<EXPIRATION_TYPE>;
    setRelativeValue: Dispatch<string>;
    setRelativeUnit: Dispatch<string>;
    setDateValue: Dispatch<string>;
    setTimeValue: Dispatch<string>;
    addChange: (change: ChangeTypeDetails) => void;
    removeChange: (index: number) => void;
    setSelfServiceRequest: Dispatch<IRequest>;
    setExpirationDate: Dispatch<string | null>;
  };
  store: {
    currentStep: SELF_SERVICE_STEPS;
    selfServiceRequest: IRequest;
    expirationType: EXPIRATION_TYPE;
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
