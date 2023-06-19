import identityIcon from 'assets/vendor/identity.svg';
import accessIcon from 'assets/vendor/access.svg';
import permissionsIcon from 'assets/vendor/permissions.svg';

const accessRegex = /access/;
const identityRegex = /iam/;

export const getRequestTypeIcon = (str: string) => {
  const text = str.toLocaleLowerCase();
  if (identityRegex.test(text)) {
    return identityIcon;
  }

  if (accessRegex.test(text)) {
    return accessIcon;
  }

  return permissionsIcon;
};
