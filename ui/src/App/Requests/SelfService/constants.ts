import { IRequest } from './types';

export enum SELF_SERVICE_STEPS {
  SELECT_PROVIDER,
  SELECT_IDENTITY,
  REQUEST_TYPE,
  CHANGE_TYPE,
  REQUEST_CHANGE_DETAILS,
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
