import { User } from './types';

export const isLoginIncomplete = (user: User | null) => {
  if (!user) {
    return true;
  }
  const {
    mfa_setup_required,
    mfa_verification_required,
    needs_to_sign_eula,
    password_reset_required
  } = user;

  console.log(user);

  return (
    mfa_setup_required ||
    mfa_verification_required ||
    needs_to_sign_eula ||
    password_reset_required
  );
};
