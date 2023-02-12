const default_user_settings = {
  editorTheme: 'vs-light'
};

export const parseLocalStorageCache = (
  key,
  default_return
): Record<string, unknown> | string => {
  const value = window.localStorage.getItem(key);
  if (value == null) {
    return default_return;
  }
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
};

export const getLocalStorageSettings = (specificSetting = '') => {
  const localStorageSettingsKey = 'NoqUserSettings';
  const localSettings = parseLocalStorageCache(
    localStorageSettingsKey,
    default_user_settings
  );

  if (!specificSetting || typeof localSettings === 'string') {
    return localSettings;
  }

  if (Object.prototype.hasOwnProperty.call(localSettings, specificSetting)) {
    return localSettings[specificSetting];
  }
  return '';
};

export const setLocalStorageSettings = settings => {
  const localStorageSettingsKey = 'NoqUserSettings';
  window.localStorage.setItem(
    localStorageSettingsKey,
    JSON.stringify(settings)
  );
};
