import { IRequest } from './types';

export enum SELF_SERVICE_STEPS {
  SELECT_PROVIDER,
  REQUEST_TYPE,
  EXPRESS_CHANGE_TYPES,
  EXPRESS_CHANGE_DETAILS,
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
  expirationDate: '',
  justification: '',
  requestedChanges: []
};

export enum EXPIRATION_TYPE {
  RELATIVE = 'RELATIVE',
  ABSOLUTE = 'ABSOLUTE',
  NEVER = 'NEVER'
}
