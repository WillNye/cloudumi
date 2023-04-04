export interface AWSOrganization {
  account_id: string;
  account_name: string;
  accounts_excluded_from_automatic_onboard: string[];
  automatically_onboard_accounts: boolean;
  automatically_onboard_accounts_options: string[];
  org_id: string;
  owner: string;
  role_names: string[];
  sync_account_names: boolean;
}
