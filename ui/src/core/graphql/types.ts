export interface GetTenantUserPoolQuery {
  client_id: string;
  user_pool_id: string;
  user_pool_region: string;
}

export interface WebResponse {
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
  data?: any;
  ssoAuthRedirect?: any;
  user?: string;
}
