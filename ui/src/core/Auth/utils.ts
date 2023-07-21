import { User } from './types';

export const isUserLoggedIn = (user: User) => {
  const {
    mfa_setup_required,
    mfa_verification_required,
    needs_to_sign_eula,
    password_reset_required
  } = user;
  return !(
    mfa_setup_required ||
    mfa_verification_required ||
    needs_to_sign_eula ||
    password_reset_required
  );
};
