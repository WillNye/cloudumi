import { PropertyFilterProps } from '@noqdev/cloudscape';
import { SUPPORTED_FILTER_KEYS } from './constants';

export const getSearchParams = (): PropertyFilterProps.Token[] => {
  const searchParams = new URLSearchParams(window.location.search);

  const keyValuePairs = [];
  for (const [key, value] of searchParams.entries()) {
    if (SUPPORTED_FILTER_KEYS.includes(key)) {
      keyValuePairs.push({
        operator: ':',
        propertyKey: key,
        value
      });
    }
  }
  return keyValuePairs;
};

export const parseRoleEnvVariable = (role: string) => role.replace(' ', '_');
