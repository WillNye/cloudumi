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
  {
    id: 'user_management',
    name: 'User Management',
    url: '/settings/user_management'
  }
];

export const BREAD_CRUMBS_AUTH_SETTINGS_PATH = [
  {
    id: 'auth_settings',
    name: 'Auth Settings',
    url: '/settings/auth_settings'
  }
];
