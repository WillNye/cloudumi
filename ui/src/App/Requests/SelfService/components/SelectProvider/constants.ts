import awsIcon from 'assets/integrations/awsIcon.svg';
import gsuiteIcon from 'assets/integrations/gsuiteIcon.svg';
import azureADIcon from 'assets/integrations/azureADIcon.svg';
import oktaIcon from 'assets/integrations/oktaIcon.svg';
import { ProviderDetails } from './types';

export const providerDetails: Record<string, ProviderDetails> = {
  aws: {
    title: 'AWS',
    icon: awsIcon,
    description: 'Amazon web services (AWS)'
  },
  okta: { title: 'Okta', icon: oktaIcon, description: 'Okta' },
  azure_ad: {
    title: 'Azure AD',
    icon: azureADIcon,
    description: 'Azure Active Directory'
  },
  google_workspace: {
    title: 'Google Workspace',
    icon: gsuiteIcon,
    description: 'Google Workspace'
  }
};
