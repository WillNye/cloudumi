import { IRequest } from './types';

export enum SELF_SERICE_STEPS {
  SELECT_PROVIDER,
  SELECT_IDENTITY,
  REQUEST_TYPE,
  CHANGE_TYPE,
  REQUEST_CHANGE_DETAILS,
  COMPLETION_FORM
}

// export const SELF_SERICE_STEPS_MAP = {
//   SELECT_PROVIDER: 1,
//   REQUEST_TYPE: 2,
//   CHANGE_TYPE: 3,
//   REQUEST_CHANGE_DETAILS: ,
//   COMPLETION_FORM; 4
// }

export const DEFAULT_REQUEST: IRequest = {
  provider: '',
  requestType: null,
  changeType: null,
  identityType: null,
  identity: null,
  expirationDate: null,
  justification: null,
  requestedChanges: []
};
