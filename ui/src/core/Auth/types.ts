export interface User {
  user: string;
  groups: string[];
  mfa_setup_required: boolean;
  eula_signed: boolean;
  password_reset_required: boolean;
}
