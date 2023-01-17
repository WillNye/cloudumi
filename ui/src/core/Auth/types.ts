export interface User {
  user: string;
  groups: string[];
  mfa_setup_required: boolean;
  eula_signed: boolean;
  password_reset_required: boolean;
  mfa_verification_required: boolean;
  needs_to_sign_eula: boolean;
}
