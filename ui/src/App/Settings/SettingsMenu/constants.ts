export enum SETTINGS_PAGE_LINKS {
  PROFILE_SETTINGS = 'PROFILE_SETTINGS',
  ACCOUNTS_MANAGEMENT = 'ACCOUNTS_MANAGEMENT',
  INTEGRATIONS = 'INTEGRATIONS'
}

export const BREAD_CRUMBS_SETTINGS_PATH = [
  { id: 'settings', name: 'Settings', url: '/settings' }
];

export const BREAD_CRUMBS_PROFILE_PATH = [
  { id: 'profile', name: 'My Profile', url: '/settings' }
];

export const BREAD_CRUMBS_INTEGRATIONS_PATH = [
  { id: 'integrations', name: 'Integrations', url: '/settings/integrations' }
];

export const BREAD_CRUMBS_ACCOUNTS_PATH = [
  { id: 'accounts', name: 'Accounts', url: '/settings/accounts' }
];
