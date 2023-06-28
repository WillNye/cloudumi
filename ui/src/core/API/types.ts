export interface IWebResponse<T> {
  data: T;
  status?: string;
  reason?: string;
  redirect_url?: string;
  status_code?: number;
  message?: string;
  errors?: string[];
  count?: number;
  total?: number;
  page?: number;
  last_page?: number;
  ssoAuthRedirect?: any;
  user?: string;
}
