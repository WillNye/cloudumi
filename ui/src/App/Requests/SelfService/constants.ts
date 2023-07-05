import { IRequest } from './types';

export enum SELF_SERVICE_STEPS {
  SELECT_PROVIDER,
  REQUEST_TYPE,
  SUGGESTED_CHANGE_TYPES,
  SELECT_IDENTITY,
  CHANGE_TYPE,
  COMPLETION_FORM
}

export const DEFAULT_REQUEST: IRequest = {
  provider: '',
  requestType: null,
  changeType: null,
  identityType: null,
  identity: null,
  expirationDate: `In 4 hours`,
  justification: '',
  requestedChanges: []
};

export enum EXPIRATION_TYPE {
  RELATIVE = 'RELATIVE',
  ABSOLUTE = 'ABSOLUTE',
  NEVER = 'NEVER'
}
