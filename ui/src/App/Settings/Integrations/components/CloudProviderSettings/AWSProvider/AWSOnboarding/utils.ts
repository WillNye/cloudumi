import { MODES } from './constants';

export const getCloudFormationUrl = (data, mode, isHubAccount) => {
  const { read_only, read_write } = data;

  if (mode === MODES.READ_ONLY) {
    const { central_account_role, spoke_account_role } = read_only;
    return isHubAccount
      ? central_account_role.cloudformation_url
      : spoke_account_role.cloudformation_url;
  }

  const { central_account_role, spoke_account_role } = read_write;
  return isHubAccount
    ? central_account_role.cloudformation_url
    : spoke_account_role.cloudformation_url;
};
