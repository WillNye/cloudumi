import React, { Dispatch } from 'react';
import { SELF_SERICE_STEPS } from './constants';

export interface RequestType {
  id: string;
  name: string;
  description: string;
  provider: string;
  supported_template_types: string[];
}

export interface ChangeType {
  id: string;
  name: string;
  description: string;
  request_type_id: string;
}

interface Typeahead {
  url: string;
  query_param_key: string;
}

export interface ChangeTypeField {
  id: string;
  change_type_id: string;
  change_element: number;
  field_key: string;
  field_value: string;
  field_type: string;
  field_text: string;
  description: string;
  allow_none: boolean;
  allow_multiple: boolean;
  options?: string[];
  typeahead?: Typeahead;
  default_value?: any;
  max_char?: number;
  validation_regex?: string;
}

export interface ChangeTypeDetails {
  id: string;
  name: string;
  description: string;
  request_type_id: string;
  fields: ChangeTypeField[];
}

export interface ISelfServiceContext {
  actions: {
    setCurrentStep: Dispatch<SELF_SERICE_STEPS>;
    setSelectedProvider: Dispatch<string>;
    setSelectedRequestType: Dispatch<RequestType>;
    setSelectedChangeType: Dispatch<ChangeType>;
    addChange: (change: ChangeTypeDetails) => void;
    removeChange: (change: ChangeTypeDetails) => void;
    goBack: () => void;
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
