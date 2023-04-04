export interface SpokeAccount {
  account_id: string;
  account_name: string;
  delegate_admin_to_owner: boolean;
  external_id: string;
  hub_account_arn: string;
  name: string;
  org_access_checked: boolean;
  org_management_account: boolean;
  owners: string[];
  read_only: boolean;
  restrict_viewers_of_account_resources: boolean;
  role_arn: string;
  viewers: string[];
}
