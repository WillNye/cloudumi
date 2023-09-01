import React, { Dispatch } from 'react';
import {
  EXPIRATION_TYPE,
  REQUEST_FLOW_MODE,
  SELF_SERVICE_STEPS
} from './constants';
import {
  ChangeTypeDetails,
  IRequest,
  RequestType,
  Identity,
  ChangeType,
  SubmittableRequest
} from './types';

export interface ISelfServiceContext {
  actions: {
    setCurrentStep: Dispatch<SELF_SERVICE_STEPS>;
    setCurrentMode: Dispatch<REQUEST_FLOW_MODE>;
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
    addChangeType: (change: ChangeType) => void;
    resetChanges: Dispatch<void>;
    removeChange: (index: number) => void;
    setSelfServiceRequest: Dispatch<IRequest>;
    setExpirationDate: Dispatch<string | null>;
    handleNext: (mode?: REQUEST_FLOW_MODE) => void;
    setExpressTemplateId: Dispatch<string>;
    setSubmittableRequest: Dispatch<SubmittableRequest | null>;
    setRevisedTemplateBody: Dispatch<string | null>;
  };
  store: {
    currentStep: SELF_SERVICE_STEPS;
    selfServiceRequest: IRequest;
    expirationType: EXPIRATION_TYPE;
    relativeValue: string;
    relativeUnit: string;
    dateValue: string;
    timeValue: string;
    revisedTemplateBody: string | null;
    submittableRequest: SubmittableRequest | null;
  };
}

const SelfServiceContext = React.createContext<ISelfServiceContext>(
  {} as ISelfServiceContext
);

export default SelfServiceContext;
