import { WebResponse } from 'core/graphql/types';

export interface IWebResponse<T> extends WebResponse {
  data?: T;
}
