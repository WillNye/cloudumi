export interface User {
  user: string;
  groups: string[];
  needs_mfa: boolean;
  eula_signed: boolean;
  password_needs_reset: boolean;
}
